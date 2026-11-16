# features/calls/api.py — wraps /api/calls (backend routers/calls.py)

from config.api import _get, _post


async def start(token, fault_id, urgency):
    return await _post(f"/api/calls/{fault_id}/start", {"urgency": urgency}, token)

async def cancel(token, fault_id):
    return await _post(f"/api/calls/{fault_id}/cancel", {}, token)

async def get_call(token, fault_id):
    return await _get(f"/api/calls/{fault_id}", token)

async def inbox(token):
    return await _get("/api/calls/inbox", token)

async def make_offer(token, fault_id, data):
    return await _post(f"/api/calls/{fault_id}/offers", data, token)

async def pass_call(token, fault_id):
    return await _post(f"/api/calls/{fault_id}/pass", {}, token)

async def accept(token, offer_id):
    return await _post(f"/api/calls/offers/{offer_id}/accept", {}, token)

async def counter(token, offer_id, fee, note=""):
    return await _post(f"/api/calls/offers/{offer_id}/counter", {"fee": fee, "note": note}, token)

async def answer(token, offer_id, accept_it: bool):
    return await _post(f"/api/calls/offers/{offer_id}/answer", {"accept": accept_it}, token)

async def withdraw(token, offer_id):
    return await _post(f"/api/calls/offers/{offer_id}/withdraw", {}, token)

async def sign_off(token, fault_id, data):
    return await _post(f"/api/calls/{fault_id}/signoff", data, token)
