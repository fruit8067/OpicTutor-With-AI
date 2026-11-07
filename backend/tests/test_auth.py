# AI-assisted: 자체 이메일/비밀번호 인증 및 세션 사용자 연결 테스트입니다.
# OWNER: session-api (contracts.yaml ownership)
from uuid import UUID, uuid4
try:
    import pytest
except ImportError:
    pytest = None
from fastapi.testclient import TestClient
from app import db
from app.main import app


def test_auth_register_login_me_session_and_logout():
    if not db.ping():
        if pytest:
            pytest.skip("로컬 PostgreSQL/pgvector 미실행")
        return
    db.init_db()
    email = f"student-{uuid4().hex[:10]}@university.ac.kr"

    with TestClient(app) as client:
        # 1. 회원가입 성공
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": f"  {email.upper()}  ", "password": "password123", "nickname": "김서준"},
        )
        assert reg.status_code == 201
        reg_body = reg.json()
        assert reg_body["user"]["email"] == email
        assert reg_body["user"]["nickname"] == "김서준"
        token = reg_body["token"]
        user_id = reg_body["user"]["id"]

        # 2. 중복 이메일 거절 (409)
        dup = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123", "nickname": "다른이름"},
        )
        assert dup.status_code == 409
        assert dup.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

        # 3. 잘못된 비밀번호 로그인 거절 (401)
        bad = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrongpassword"},
        )
        assert bad.status_code == 401
        assert bad.json()["error"]["code"] == "INVALID_CREDENTIALS"

        # 4. 정상 로그인 (200)
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        assert login_res.status_code == 200
        login_token = login_res.json()["token"]
        assert login_res.json()["user"]["id"] == user_id

        # 5. /auth/me 조회
        me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login_token}"})
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

        # 6. 로그인 토큰으로 시험 세션 생성 시 sessions.user_id 기록 확인
        sess_res = client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {login_token}"},
            json={"client_request_id": f"auth-req-{uuid4()}", "scenario_id": "default", "mic_check_passed": True},
        )
        assert sess_res.status_code == 202
        sid = UUID(sess_res.json()["session_id"])
        row = db.get_session(sid)
        assert row is not None and str(row["user_id"]) == user_id

        # 6-1. 내 시험 히스토리 목록 조회 확인
        hist_res = client.get("/api/v1/sessions/history", headers={"Authorization": f"Bearer {login_token}"})
        assert hist_res.status_code == 200
        hist_body = hist_res.json()
        assert hist_body["summary"]["total_sessions"] == 1
        assert hist_body["summary"]["in_progress_sessions"] == 1
        assert hist_body["items"][0]["session_id"] == str(sid)

        # 6-2. 다른 유저(User B) 가입 후 User A의 세션 조회/삭제 시도 시 403 FORBIDDEN 차단 확인
        email_b = f"other-{uuid4().hex[:10]}@university.ac.kr"
        reg_b = client.post(
            "/api/v1/auth/register",
            json={"email": email_b, "password": "password123", "nickname": "박지민"},
        )
        assert reg_b.status_code == 201
        token_b = reg_b.json()["token"]
        user_b_id = reg_b.json()["user"]["id"]

        hist_b = client.get("/api/v1/sessions/history", headers={"Authorization": f"Bearer {token_b}"})
        assert hist_b.status_code == 200
        assert hist_b.json()["summary"]["total_sessions"] == 0

        forbid_get = client.get(f"/api/v1/sessions/{sid}", headers={"Authorization": f"Bearer {token_b}"})
        assert forbid_get.status_code == 403
        assert forbid_get.json()["error"]["code"] == "FORBIDDEN"

        forbid_del = client.delete(f"/api/v1/sessions/{sid}", headers={"Authorization": f"Bearer {token_b}"})
        assert forbid_del.status_code == 403
        assert forbid_del.json()["error"]["code"] == "FORBIDDEN"

        # 6-3. 본인(User A)이 세션 삭제 시 정상 삭제 확인
        del_res = client.delete(f"/api/v1/sessions/{sid}", headers={"Authorization": f"Bearer {login_token}"})
        assert del_res.status_code == 200
        assert del_res.json()["ok"] is True

        hist_after_del = client.get("/api/v1/sessions/history", headers={"Authorization": f"Bearer {login_token}"})
        assert hist_after_del.status_code == 200
        assert hist_after_del.json()["summary"]["total_sessions"] == 0

        # 7. 로그아웃 후 토큰 무효화 확인 (401)
        out_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {login_token}"})
        assert out_res.status_code == 200
        assert out_res.json()["ok"] is True

        me_after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login_token}"})
        assert me_after.status_code == 401
        assert me_after.json()["error"]["code"] == "UNAUTHORIZED"

        # 정리
        from app.db.pool import tx
        with tx() as cur:
            cur.execute("DELETE FROM users WHERE id IN (%s, %s)", (UUID(user_id), UUID(user_b_id)))
            assert cur.rowcount == 2
        assert db.get_user_by_token(token) is None
