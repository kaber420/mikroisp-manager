import asyncio
import uuid
from sqlmodel import SQLModel
from app.db.engine_sync import sync_engine as engine
from app.models import Client
from app.services.client_service import ClientService
from sqlmodel import Session

async def main():
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        service = ClientService(session)
        print("Creating client...")
        try:
            client_data = {
                "name": "Test Client UUID",
                "service_status": "active"
            }
            new_client = service.create_client(client_data)
            print(f"Client Created: {new_client}")
            
            client_id = new_client['id']
            print(f"Client ID: {client_id} (Type: {type(client_id)})")
            
            if isinstance(client_id, uuid.UUID):
                print("SUCCESS: Client ID is a UUID")
            else:
                try:
                    uuid.UUID(str(client_id))
                    print("SUCCESS: Client ID is a valid UUID string")
                except ValueError:
                    print(f"FAILURE: Client ID is NOT a UUID: {client_id}")
                    
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
