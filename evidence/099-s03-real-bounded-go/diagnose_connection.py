"""One-off diagnostic: why the modeld grant connection is refused. Prints the real reason."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.test_core_work_real import RealBoundedAcceptanceTests  # noqa: E402

case = RealBoundedAcceptanceTests("test_one_work_uses_at_most_two_calls_and_reports_usage_without_cost")
case.setUp()
try:
    au_id = case.prepare()
    grant_ref, grant_revision = case.grant(au_id)
    print("grant", grant_ref, "revision", grant_revision)
    data = case.connection(grant_ref, grant_revision)
    status, value, _ = case.model_command("save_connection", data)
    print("save status", status, json.dumps(value.get("receipt"), ensure_ascii=False)[:300])
    operation_id = value["receipt"].get("operation_id")
    models = case.read()["au"]["model_access"]
    print("operation", json.dumps(models["operations"].get(operation_id), ensure_ascii=False)[:400])
    if operation_id:
        try:
            case.app.models.save_connection(au_id, operation_id, None, False)
            print("direct save returned")
        except Exception as error:  # noqa: BLE001 - diagnostic only
            print("direct save raised:", type(error).__name__, str(error)[:300])
        try:
            client = case.app.models.backend()
            config = models["operations"][operation_id]["config"]
            raw = client.call("GET", "/v1/grants/" + config["grant_ref"], admin=True)
            print("grant readback:", json.dumps({k: raw.get(k) for k in ("id", "au_id", "revision", "model_ids", "revoked_at")}, ensure_ascii=False))
            print("config compares:", json.dumps({"au_id": au_id, "grant_ref": config["grant_ref"], "revision": config["grant_revision"], "model": config["model"]}, ensure_ascii=False))
            grant = case.app.models.check_grant(client, au_id, config)
            print("check_grant ok", json.dumps(grant, ensure_ascii=False)[:200])
            case.app.models.check_operation(models, models["operations"][operation_id], {case.principal})
            print("check_operation ok")
        except Exception as error:  # noqa: BLE001 - diagnostic only
            print("check raised:", type(error).__name__, str(error)[:300])
        models = case.read()["au"]["model_access"]
        print("after", json.dumps(models["operations"].get(operation_id), ensure_ascii=False)[:400])
finally:
    case.stop()
