"""Shared rejection types; transport codes do not grant runtime authority."""


class Rejected(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Rejected(reason)


class CoreError(Rejected):
    STATUS = {"not_authenticated": 401, "not_authorized": 403, "invalid_request": 400,
              "id_conflict": 409, "incompatible_state": 409, "unsupported_capability": 409,
              "storage_unavailable": 503}

    def __init__(self, code, message=None):
        self.code = code
        self.status = self.STATUS[code]
        defaults = {"not_authenticated": "请登录核心账户", "not_authorized": "当前核心账户无权访问此记录",
                    "unsupported_capability": "此 AU 尚在准备态，自主行动与资源操作尚未启用"}
        super().__init__(message or defaults.get(code, "核心请求无法完成"))
