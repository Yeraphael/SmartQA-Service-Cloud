from fastapi.routing import APIRoute


class OperationLogRoute(APIRoute):
    """Compatibility route class; SmartQA does not expose template operation logs."""

    pass
