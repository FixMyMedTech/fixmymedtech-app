# features/onboarding/api.py — wraps /api/onboarding (backend routers/onboarding.py)

from urllib.parse import quote

from config.api import _get, _post, _delete


async def get_me(token):
    return await _get("/api/onboarding/me", token)


async def invite_clinic(token, email, message):
    return await _post("/api/onboarding/clinic-invitations", {"email": email, "message": message}, token)


async def my_clinic_invitations(token):
    return await _get("/api/onboarding/clinic-invitations", token)


async def my_clinics(token):
    return await _get("/api/onboarding/my-clinics", token)


async def get_invitation(invite_token):
    return await _get(f"/api/onboarding/invitations/{quote(invite_token)}")


async def accept_invitation(invite_token, full_name, password):
    return await _post(f"/api/onboarding/invitations/{quote(invite_token)}/accept",
                       {"full_name": full_name, "password": password})


async def claim_invitation(token, invite_token):
    return await _post(f"/api/onboarding/invitations/{quote(invite_token)}/claim", {}, token)


async def clinic_search(token, lat=None, lng=None, q=""):
    if lat is not None and lng is not None:
        return await _get(f"/api/onboarding/clinic/search?lat={lat}&lng={lng}", token)
    return await _get(f"/api/onboarding/clinic/search?q={quote(q)}", token)


async def clinic_pick(token, facility: dict):
    return await _post("/api/onboarding/clinic/pick", facility, token)


async def clinic_create(token, data: dict):
    return await _post("/api/onboarding/clinic/create", data, token)


async def clinic_mine(token):
    return await _get("/api/onboarding/clinic/mine", token)


async def clinic_engineers(token, org_id):
    return await _get(f"/api/onboarding/clinics/{org_id}/engineers", token)


async def add_engineer(token, org_id, email, kind):
    return await _post(f"/api/onboarding/clinics/{org_id}/engineers", {"email": email, "kind": kind}, token)


async def confirm_engineer(token, org_id, engineer_id):
    return await _post(f"/api/onboarding/clinics/{org_id}/engineers/{engineer_id}/confirm", {}, token)


async def not_now_engineer(token, org_id, engineer_id):
    return await _post(f"/api/onboarding/clinics/{org_id}/engineers/{engineer_id}/not-now", {}, token)


async def remove_engineer(token, org_id, engineer_id):
    return await _delete(f"/api/onboarding/clinics/{org_id}/engineers/{engineer_id}", token)


async def cancel_engineer_invitation(token, org_id, invitation_id):
    return await _delete(f"/api/onboarding/clinics/{org_id}/invitations/{invitation_id}", token)


async def registrable_clinics(token):
    return await _get("/api/onboarding/registrable-clinics", token)


async def host_applicants(token):
    return await _get("/api/onboarding/host/applicants", token)


async def host_confirm_talk(token, profile_id):
    return await _post(f"/api/onboarding/host/applicants/{profile_id}/talk", {}, token)


async def host_clinics(token):
    return await _get("/api/onboarding/host/clinics", token)


async def host_unlock_clinic(token, org_id):
    return await _post(f"/api/onboarding/host/clinics/{org_id}/unlock", {}, token)
