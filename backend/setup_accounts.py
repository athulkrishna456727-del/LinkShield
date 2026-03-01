import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import uuid
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def create_default_accounts():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    # Owner Account
    owner_email = 'athulkrishna456727@gmail.com'
    existing_owner = await db.users.find_one({'email': owner_email})
    if not existing_owner:
        password_hash = bcrypt.hashpw('#AThr401012#'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        owner_doc = {
            'id': str(uuid.uuid4()),
            'email': owner_email,
            'password_hash': password_hash,
            'name': 'System Owner',
            'role': 'owner',
            'plan': 'enterprise',
            'credits': 999999,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(owner_doc)
        print(f'✓ Owner account created: {owner_email}')
    else:
        print(f'✓ Owner account already exists: {owner_email}')
    
    # Admin Account
    admin_email = 'athulmark401012@gmail.com'
    existing_admin = await db.users.find_one({'email': admin_email})
    if not existing_admin:
        password_hash = bcrypt.hashpw('dgskgsnskz'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        admin_doc = {
            'id': str(uuid.uuid4()),
            'email': admin_email,
            'password_hash': password_hash,
            'name': 'System Admin',
            'role': 'admin',
            'plan': 'premium',
            'credits': 1000,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(admin_doc)
        print(f'✓ Admin account created: {admin_email}')
    else:
        print(f'✓ Admin account already exists: {admin_email}')
    
    client.close()
    print('\n=== Default Accounts ===')
    print(f'Owner: {owner_email} / #AThr401012#')
    print(f'Admin: {admin_email} / dgskgsnskz')

if __name__ == '__main__':
    asyncio.run(create_default_accounts())