from __future__ import annotations

class HodgeCYError(Exception):
    pass

class IdentityError(HodgeCYError, ValueError):
    pass

class SerializationError(HodgeCYError, ValueError):
    pass

class ValidationError(HodgeCYError, ValueError):
    pass

class ConfigurationError(HodgeCYError, ValueError):
    pass
