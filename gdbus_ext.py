"""
PyGObject DBus extensions.
This is temporary and will be contributed to PyGObject.
"""
from __future__ import annotations

import os
from functools import partial, partialmethod
from typing import (
    Optional,
    Literal,
    Union,
    Callable,
    Protocol,
    Tuple,
    ClassVar,
    Set,
    Dict,
    List,
    Any,
)

from gi.repository import Gio, GLib


_DBusHandlerType = Union[
    Literal["method"],
    Literal["signal"],
    Literal["property_get"],
    Literal["property_set"],
]
_NotUnique = None
_InterfacesType = List[Gio.DBusInterfaceInfo]
# outer key: interface name; inner key: method name
_MethodsType = Dict[str, Dict[str, Tuple[Gio.DBusMethodInfo, Callable]]]
# outer key: interface name; inner key: property name; tuple members: info, getter, setter
_PropertiesType = Dict[
    str,
    Dict[str, Tuple[Gio.DBusPropertyInfo, Callable, Callable]],
]
_UniqueElementsType = Dict[str, Union[Gio.DBusInterfaceInfo, _NotUnique]]


class DBusHandlerStandIn:
    def __init__(
        self, typ: _DBusHandlerType, name: str, func: Callable, interface: Optional[str]
    ):
        self.type = typ
        self.name = name
        self.func = func
        self.interface = interface


_OpenPropsType = Dict[Tuple[str, str], DBusHandlerStandIn]


def to_pascal_case(input_str):
    def _capitalize_parts(words):
        for word in words:
            if len(word) < 2:
                yield word.capitalize()
            else:
                yield word[0].capitalize() + word[1:]

    return "".join(_capitalize_parts(input_str.split("_")))


def generate_name(
    maybe_name: Optional[str], func, remove_prefix: Optional[str] = None
) -> str:
    if maybe_name is not None:
        return maybe_name
    if hasattr(func, "__name__"):
        basename = func.__name__
        if remove_prefix is not None and basename.startswith(remove_prefix):
            basename = basename[len(remove_prefix) :]
        return to_pascal_case(basename)
    raise NameError("the method decorated has no name and no name was given")


class Method:
    """
    Decorator. Handler for a D-Bus method.

    The method will be passed all the arguments used.
    It must return None when no out arguments are defined.
    If one out argument is defined it may either return a tuple with one element or the output argument directly.
    If more out arguments are defined, it must return them all in a tuple.

    The decorated method must not have kwargs or keyword-only arguments.
    """

    def __init__(self, name: Optional[str] = None, interface: Optional[str] = None):
        """
        `name` is the name of the method.
        If `name` is not set, the name is generated to be the
        PascalCase version of the decorated method name.

        `interface` is the name of the interface that this method is defined on.
        This will usually be auto-detected based on the method name, however if
        there is a conflict it needs to be set manually.
        """
        self._name = name
        self._interface = interface

    def __call__(self, func):
        return DBusHandlerStandIn(
            "method", generate_name(self._name, func), func, self._interface
        )


class Signal:
    """
    Decorator. Emitter for a D-Bus signal.

    If `name` is not set, the name is generated to be the PascalCase version of the decorated
    method name.

    The decorated method gets all the arguments that are supposed to be sent in. It
    may return a tuple to override the arguments to send (it must be the same number and
    compatible types). Otherwise, it must just return None.

    The decorated method must not have kwargs or keyword-only arguments.
    """

    def __init__(self, name: Optional[str] = None, interface: Optional[str] = None):
        """
        `name` is the name of the signal.
        If `name` is not set, the name is generated to be the PascalCase version of the decorated
        method name.

        `interface` is the name of the interface that this method is defined on.
        This will usually be auto-detected based on the method name, however if
        there is a conflict it needs to be set manually.
        """
        self._name = name
        self._interface = interface

    def __call__(self, func):
        return DBusHandlerStandIn(
            "signal", generate_name(self._name, func), func, self._interface
        )


class PropertyGet:
    """
    Decorator. Decorated methods handle getting a property.

    The decorated method must not have kwargs or keyword-only arguments.
    """

    def __init__(self, name: Optional[str] = None, interface: Optional[str] = None):
        """
        `name` is the name of the property.
        If `name` is not set, the name is generated to be the PascalCase version of the decorated
        method name.
        Any `get_` at the beginning of the decorated method name is removed before this is done.

        `interface` is the name of the interface that this method is defined on.
        This will usually be auto-detected based on the method name, however if
        there is a conflict it needs to be set manually.
        """
        self._name = name
        self._interface = interface

    def __call__(self, func):
        return DBusHandlerStandIn(
            "property_get",
            generate_name(self._name, func, "get_"),
            func,
            self._interface,
        )


class PropertySet:
    """
    Decorator. Decorated methods handle setting a property.

    The decorated method must not have kwargs or keyword-only arguments.

    Calling the setter, either from Python or remotely via D-Bus, will also emit the
    `org.freedesktop.DBus.Properties.PropertiesChanged` signal.
    """

    pass

    def __init__(self, name: Optional[str] = None, interface: Optional[str] = None):
        """
        `name` is the name of the property.
        If `name` is not set, the name is generated to be the PascalCase version of the decorated
        method name.
        Any `set_` at the beginning of the decorated method name is removed before this is done.

        `interface` is the name of the interface that this method is defined on.
        This will usually be auto-detected based on the method name, however if
        there is a conflict it needs to be set manually.
        """
        self._name = name
        self._interface = interface

    def __call__(self, func):
        return DBusHandlerStandIn(
            "property_set",
            generate_name(self._name, func, "set_"),
            func,
            self._interface,
        )


class IsDecorated(Protocol):
    __giodbustemplate__interfaces__: ClassVar[_InterfacesType]
    __giodbustemplate__methods__: ClassVar[_MethodsType]
    __giodbustemplate__properties__: ClassVar[_PropertiesType]

    __giodbustemplate__connection__: Gio.DBusConnection
    __giodbustemplate__path__: str


def on_method_call(
    obj: IsDecorated,
    _connection: Gio.DBusConnection,
    _sender: str,
    _object_path: str,
    interface_name: str,
    method_name: str,
    parameters: GLib.Variant,
    invocation: Gio.DBusMethodInvocation,
):
    methods = obj.__class__.__giodbustemplate__methods__
    method_info, method_func = methods[interface_name][method_name]
    args = list(parameters.unpack())

    try:
        result = method_func(obj, *args)
    except ValueError as e:
        invocation.return_dbus_error(interface_name, str(e))
        return

    if not isinstance(result, tuple):
        result = (result,)

    out_args = "(" + "".join((arg.signature for arg in method_info.out_args)) + ")"

    if out_args != "()":
        variant = GLib.Variant(out_args, result)
        invocation.return_value(variant)
    else:
        invocation.return_value(None)


def on_get_property(
    obj: IsDecorated,
    _connection: Gio.DBusConnection,
    _sender: str,
    _object_path: str,
    interface_name: str,
    property_name: str,
):
    properties = obj.__class__.__giodbustemplate__properties__
    prop_info, getter, _setter = properties[interface_name][property_name]
    value = getter(obj)
    return GLib.Variant(prop_info.signature, value)


def on_set_property(
    obj: IsDecorated,
    _connection: Gio.DBusConnection,
    _sender: str,
    _object_path: str,
    interface_name: str,
    property_name: str,
    value: GLib.Variant,
):
    properties = obj.__class__.__giodbustemplate__properties__
    _prop_info, _getter, setter = properties[interface_name][property_name]
    setter(obj, value.unpack())
    # we emit the org.freedesktop.DBus.Properties.PropertiesChanged signal.
    emit_signal(
        obj,
        "PropertiesChanged",
        "org.freedesktop.DBus.Properties",
        obj.__giodbustemplate__path__,
        GLib.Variant.new_tuple(
            GLib.Variant("s", interface_name),
            GLib.Variant("a{sv}", {property_name: value}),
            GLib.Variant("as", []),
        ),
    )
    return True  # if setting failed, the setter would have raised an exception.


def handle_signal_method(
    obj: IsDecorated,
    info: Gio.DBusSignalInfo,
    func: Callable,
    interface_name: str,
    *original_arguments,
):
    maybe_new_values = func(obj, *original_arguments)
    if maybe_new_values is not None:
        if not isinstance(maybe_new_values, tuple):
            maybe_new_values = (maybe_new_values,)
        if len(maybe_new_values) != len(original_arguments):
            raise AssertionError("signal emitter returned invalid number of arguments.")
        values = maybe_new_values
    else:
        values = original_arguments

    parameters = []
    for value, arg in zip(values, info.args):
        parameters.append(GLib.Variant(arg.signature, value))
    variant = GLib.Variant.new_tuple(*parameters)

    emit_signal(obj, info.name, interface_name, obj.__giodbustemplate__path__, variant)


def emit_signal(
    obj: IsDecorated,
    signal_name: str,
    interface_name: str,
    path: str,
    parameters: GLib.Variant,
):
    obj.__giodbustemplate__connection__.emit_signal(
        None, path, interface_name, signal_name, parameters
    )


def not_supported_setter(*args):
    raise TypeError("this property is read-only")


def ent_name(standin: DBusHandlerStandIn):
    if standin.type == "property_get" or standin.type == "property_set":
        return "property"
    return standin.type


def process_standin(
    standin: DBusHandlerStandIn,
    unassigned: Set[Tuple[str, str]],
    unique: _UniqueElementsType,
    infos: Dict[str, Dict[str, Any]],
    # not set for signals, we don't need to record them in the class, the partials themselves contain everything needed:
    runtime_def=None,
    # only set if processing property getter or setter:
    open_props: Optional[_OpenPropsType] = None,
) -> str:
    if standin.interface is not None:
        interface_name = standin.interface
    else:
        if standin.name not in unique:
            raise TypeError(
                f"D-Bus {ent_name(standin)} {standin.name} not defined in any interface"
            )
        if unique[standin.name] is None:
            type_name = ent_name(standin)
            raise TypeError(
                f"Interface for D-Bus {type_name} {standin.name} could not be auto-detected since the {type_name} is defined in multiple interfaces. Specify the interface name manually"
            )
        interface_name = unique[standin.name].name

    if interface_name not in infos:
        raise TypeError(f"D-Bus interface {interface_name} not defined")

    if standin.name not in infos[interface_name]:
        raise TypeError(
            f"D-Bus {ent_name(standin)} {standin.name} not defined for interface {interface_name}"
        )

    ident = (interface_name, standin.name)

    if ident not in unassigned:
        raise TypeError(
            f"D-Bus {ent_name(standin)} {standin.name} has a handler method but is either not in the XML or there are multiple handlers defined for it in class"
        )

    if runtime_def is not None:
        if interface_name not in runtime_def:
            runtime_def[interface_name] = {}

        info = infos[interface_name][standin.name]
        if standin.type == "property_get" or standin.type == "property_set":
            assert open_props is not None
            if ident in open_props:
                counterpart = open_props[ident]
                if {counterpart.type, standin.type} != {"property_get", "property_set"}:
                    raise TypeError(
                        f"D-Bus {ent_name(standin)} {standin.name} has multiple getters and/or setters defined"
                    )

                if standin.type == "property_get":
                    runtime_def[interface_name][standin.name] = (
                        info,
                        standin.func,
                        counterpart.func,
                    )
                else:
                    runtime_def[interface_name][standin.name] = (
                        info,
                        counterpart.func,
                        standin.func,
                    )

                del open_props[ident]
                unassigned.remove(ident)
            else:
                open_props[ident] = standin
        else:
            runtime_def[interface_name][standin.name] = (
                info,
                standin.func,
            )
            unassigned.remove(ident)
    else:
        unassigned.remove(ident)

    return interface_name


def collect_unassigned(infos: dict[str, dict[str, Any]]):
    for intf_name, objs in infos.items():
        for obj_name in objs.keys():
            yield intf_name, obj_name


class DBusTemplate:
    """
    Decorator to turn instances of Python classes into D-Bus objects.

    When a class is decorated, the XML D-Bus introspection is checked for properties, signals and methods.

    - For each method in the interfaces the class must have a matching decorated `DBusTemplate.Method` method.
    -  For each signal in the interfaces the class must have a matching decorated `DBusTemplate.Signal` method.
    -  For each property in the interfaces the class must have both a matching decorated `DBusTemplate.PropertyGet`
       and optionally a `DBusTemplate.PropertySet` method. If no setter is defined, a default one is generated,
       which will just raise a type error. Useful for read-only properties.

    If any of these is not the case or if the class as any additional methods, signals or properties defined
    a TypeError is raised.

    The XML introspection file should not contain definitions of the `org.freedesktop.DBus.Properties`,
    `org.freedesktop.Peer` or `org.freedesktop.DBus.Introspectable` interfaces. Implementations for these are
    always provided.

    The decorated class and objects created by it must have a `__dict__`.

    Use `DBusTemplate.register_object` to register an object decorated this way on a connection.
    """

    Method = Method
    Signal = Signal
    PropertyGet = PropertyGet
    PropertySet = PropertySet

    @classmethod
    def register_object(cls, connection: Gio.DBusConnection, name: str, path: str, obj):
        """Register an object of a class decorated with `DBusTemplate` on the given `DBusConnection`."""
        if not hasattr(obj.__class__, "__giodbustemplate__interfaces__"):
            raise TypeError(
                "register_object must be called for object decorated with DBusTemplate"
            )

        if hasattr(obj, "__giodbustemplate__connection__"):
            raise TypeError("register_object can only be called once for an object")

        setattr(obj, "__giodbustemplate__connection__", connection)
        setattr(obj, "__giodbustemplate__path__", path)

        Gio.bus_own_name_on_connection(
            connection, name, Gio.BusNameOwnerFlags.NONE, None, None
        )

        for interface in obj.__class__.__giodbustemplate__interfaces__:
            connection.register_object(
                object_path=path,
                interface_info=interface,
                method_call_closure=partial(on_method_call, obj),
                get_property_closure=partial(on_get_property, obj),
                set_property_closure=partial(on_set_property, obj),
            )

    def __init__(
        self,
        *,
        # Introspection XML
        # One of these must be defined:
        string: Optional[str] = None,
        filename: Optional[str] = None,
    ):
        self.string = string
        self.filename = filename

        if self.string is None and self.filename is None:
            raise TypeError("Requires one of the following arguments: string, filename")

    def __call__(self, cls):
        if self.string is not None:
            xml_data = self.string
        else:
            assert self.filename is not None
            file_ = Gio.File.new_for_path(os.fspath(self.filename))
            xml_data = str(file_.load_contents()[1], "utf-8")

        # These dicts are for looking up infos during class traversal
        infos_methods: Dict[str, Dict[str, Gio.DBusMethodInfo]] = {}
        infos_signals: Dict[str, Dict[str, Gio.DBusSignalInfo]] = {}
        infos_properties: Dict[str, Dict[str, Gio.DBusPropertyInfo]] = {}

        # These dicts contain the names of methods signals and properties of all that are defined.
        # Those that are only defined within a single interface have that interface's info as value.
        # They are allowed to have the interface name omitted in the method/signal/property decorators,
        # they will be automatically assigned. The others have None as value.
        unique_methods: _UniqueElementsType = {}
        unique_signals: _UniqueElementsType = {}
        unique_properties: _UniqueElementsType = {}

        # The definitions we later actually need to store on the class.
        def_interfaces: _InterfacesType = []
        def_methods: _MethodsType = {}
        def_properties: _PropertiesType = {}

        # Collect interface infos
        for interface in Gio.DBusNodeInfo.new_for_xml(xml_data).interfaces:
            infos_methods[interface.name] = {}
            infos_signals[interface.name] = {}
            infos_properties[interface.name] = {}

            for method in interface.methods:
                infos_methods[interface.name][method.name] = method
                if method.name not in unique_methods:
                    unique_methods[method.name] = interface
                else:
                    unique_methods[method.name] = _NotUnique

            for signal in interface.signals:
                infos_signals[interface.name][signal.name] = signal
                if signal.name not in unique_signals:
                    unique_signals[signal.name] = interface
                else:
                    unique_signals[signal.name] = _NotUnique

            for prop in interface.properties:
                infos_properties[interface.name][prop.name] = prop
                if prop.name not in unique_properties:
                    unique_properties[prop.name] = interface
                else:
                    unique_properties[prop.name] = _NotUnique

            def_interfaces.append(interface)

        # Keep sets of all methods, signals and properties we have not yet found in the class.
        unassigned_methods = set(collect_unassigned(infos_methods))
        unassigned_signals = set(collect_unassigned(infos_signals))
        unassigned_properties = set(collect_unassigned(infos_properties))

        # This dict keeps track of "open" properties: properties where we have found a getter or setter but not both.
        open_props: _OpenPropsType = {}

        # Collect methods, signals, property handler methods in cls
        for attr_name, member in cls.__dict__.items():
            if isinstance(member, DBusHandlerStandIn):
                if member.type == "method":
                    process_standin(
                        member,
                        unassigned_methods,
                        unique_methods,
                        infos_methods,
                        def_methods,
                    )
                    # Replace method again with actual method
                    setattr(cls, attr_name, member.func)
                elif member.type == "signal":
                    interface_name = process_standin(
                        member,
                        unassigned_signals,
                        unique_signals,
                        infos_signals,
                    )
                    # For signals we replace the method itself with a special proxy partial
                    setattr(
                        cls,
                        attr_name,
                        # handle_signal_method will get self as the first argument,
                        # it will then get all the parameters defined below
                        # and then the additional arguments of the call itself.
                        partialmethod(
                            handle_signal_method,
                            infos_signals[interface_name][member.name],
                            member.func,
                            interface_name,
                        ),
                    )
                else:
                    assert (
                        member.type == "property_set" or member.type == "property_get"
                    )
                    process_standin(
                        member,
                        unassigned_properties,
                        unique_properties,
                        infos_properties,
                        def_properties,
                        open_props,
                    )
                    # Replace method again with actual method
                    setattr(cls, attr_name, member.func)

        # Validate that all are accounted for and generate default setters
        open_pros_iter = iter(open_props.items())
        for (interface_name, prop_name), existing_standin in open_pros_iter:
            if existing_standin.type == "property_get":
                # Insert default setter
                info = infos_properties[interface_name][existing_standin.name]
                def_properties[interface_name][existing_standin.name] = (
                    info,
                    existing_standin.func,
                    not_supported_setter,
                )
                unassigned_properties.remove((interface_name, existing_standin.name))
            else:
                assert existing_standin.type == "property_set"
                raise TypeError(
                    f"Missing getter for interface property '{prop_name}' from interface '{interface_name}'"
                )

        if len(unassigned_methods) > 0:
            interface_name, method_name = next(iter(unassigned_methods))
            raise TypeError(
                f"Missing handler for interface method '{method_name}' from interface '{interface_name}'"
            )
        if len(unassigned_signals) > 0:
            interface_name, signal_name = next(iter(unassigned_signals))
            raise TypeError(
                f"Missing handler for interface signal '{signal_name}' from interface '{interface_name}'"
            )
        if len(unassigned_properties) > 0:
            interface_name, prop_name = next(iter(unassigned_properties))
            raise TypeError(
                f"Missing handlers for interface property '{prop_name}' from interface '{interface_name}'"
            )

        # Store the definitions we need at runtime
        setattr(cls, "__giodbustemplate__interfaces__", def_interfaces)
        setattr(cls, "__giodbustemplate__methods__", def_methods)
        setattr(cls, "__giodbustemplate__properties__", def_properties)
        # __giodbustemplate__connection__ and __giodbustemplate__path__ are
        # set on an object of this class by register_object.
        return cls


__all__ = ["DBusTemplate"]
