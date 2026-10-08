import urllib.request
import json

base_url = 'http://127.0.0.1:8000'

def test_user_flow():
    print("=== TEST 1: LIST USERS ===")
    req = urllib.request.Request(f"{base_url}/api/users/")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print(f"Users found: {len(data.get('users', []))}, Summary: {data.get('summary')}")
        
    print("\n=== TEST 2: CREATE USER ===")
    create_payload = {
        "username": "juan.perez.test",
        "full_name": "Juan Pérez Test",
        "rut": "16.543.210-K",
        "email": "juan.perez.test@laserena.cl",
        "password": "PasswordTest2026!",
        "status": "Activo",
        "delegation_id": 2,
        "position_id": 3,
        "role_ids": [4]
    }
    req = urllib.request.Request(
        f"{base_url}/api/users/create/",
        data=json.dumps(create_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Create response:", res)
        user_id = res.get('user_id')

    if user_id:
        print(f"\n=== TEST 3: TOGGLE STATUS (User #{user_id}) ===")
        req = urllib.request.Request(
            f"{base_url}/api/users/{user_id}/toggle-status/",
            data=b"{}",
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print("Toggle status response:", res)

        print(f"\n=== TEST 4: DELETE USER (User #{user_id}) ===")
        req = urllib.request.Request(
            f"{base_url}/api/users/{user_id}/delete/",
            data=b"{}",
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print("Delete response:", res)

    print("\n=== TEST 5: CREATE ATENCION ===")
    atencion_payload = {
        "title": "Postulación RSH Vecino Test",
        "description": "Se ingresan documentos socioeconómicos y comprobante domiciliario.",
        "delegation": "Centro Histórico",
        "contact_name": "Valeria Rojas Test",
        "contact_phone": "+56 9 9876 5432",
        "status": "Approved"
    }
    req = urllib.request.Request(
        f"{base_url}/api/atenciones/",
        data=json.dumps(atencion_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Atención create response:", res)

    print("\n=== TEST 6: TOGGLE PERMISO ROL ===")
    rol_payload = {
        "rol_name": "Funcionario",
        "permiso": "lectura",
        "enabled": True
    }
    req = urllib.request.Request(
        f"{base_url}/api/roles/toggle-permiso/",
        data=json.dumps(rol_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Role permission toggle response:", res)

if __name__ == '__main__':
    test_user_flow()
