from secrets import token_urlsafe

from fastapi.testclient import TestClient

from super_agent_voice import ledger, policy
from super_agent_voice.app import create_app
from super_agent_voice.config import VoiceConfig


def test_hq_jobs_enforce_boundary_roles_and_revision(monkeypatch, tmp_path):
    secret = token_urlsafe(32)
    monkeypatch.setenv("SUPER_AGENT_HQ_LEDGER_TOKEN", secret)
    monkeypatch.setattr(ledger, "DB_PATH", tmp_path / "ledger.sqlite")
    host = "http://127.0.0.1:8000"
    with TestClient(create_app(VoiceConfig(local_token=token_urlsafe(32))), base_url=host) as client:
        def post(role, operation, body, **headers):
            return client.post(f"/api/jobs/{role}/{operation}", json=body, headers={
                "Authorization": f"Bearer {secret}", **headers,
            })

        assert post("scout", "claim", {}, Host="localhost:8000").status_code == 403
        assert post("scout", "claim", {}, Origin=host).status_code == 403
        assert post("scout", "claim", {}, Authorization="Bearer incorrect").status_code == 403
        assert post("invented", "claim", {}).status_code == 400

        payload = {"key": "a" * 32, "instruction": "Give a synthetic example"}
        assert post("scout", "submit", {**payload, "data_class": "synthetic"}).status_code == 400
        ident = post("scout", "submit", payload).json()["id"]
        assert post("scout", "submit", payload).json()["id"] == ident
        assert post("forge", "claim", {}).json() == {"job": None}
        personal = ledger.create_job({"task_type": "answer", "instruction": "private", "data_class": "personal"}, "personal")
        assert ledger.claim_next_job().id == personal.id
        scout = post("scout", "claim", {}).json()["job"]
        assert scout["id"] == ident
        assert post("scout", "claim", {}).json() == {"job": None}
        assert ledger.recover_after_restart() == 1
        assert ledger.get_job(ident).state == "running"

        receipt = {"id": ident, "revision": scout["revision"], "state": "succeeded", "summary": "Example done", "artifacts": ["report.txt"]}
        assert post("scout", "finish", {**receipt, "artifacts": ["../private"]}).status_code == 400
        assert post("forge", "finish", receipt).status_code == 403
        assert post("scout", "finish", receipt).status_code == 200
        assert post("scout", "finish", receipt).status_code == 200
        assert len(ledger.list_events(ident)) == 3
        assert post("scout", "finish", {**receipt, "summary": "different"}).status_code == 400
        assert ledger.list_events(ident)[-1].receipt == {"summary": "Example done", "artifacts": ["report.txt"]}
        assert post("scout", "submit", {**payload, "key": "b" * 32, "instruction": "x" * (policy.Limits().instruction_chars + 1)}).status_code == 400
