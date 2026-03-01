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

async def create_admin():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    
    # Check if admin exists
    existing = await db.users.find_one({'email': 'admin@linkshield.com'})
    if existing:
        print('Admin user already exists')
        client.close()
        return
    
    # Create admin user
    password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_doc = {
        'id': str(uuid.uuid4()),
        'email': 'admin@linkshield.com',
        'password_hash': password_hash,
        'name': 'Admin User',
        'role': 'admin',
        'plan': 'premium',
        'credits': 1000,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(admin_doc)
    print('✓ Admin user created successfully')
    print('  Email: admin@linkshield.com')
    print('  Password: admin123')
    
    client.close()

if __name__ == '__main__':
    asyncio.run(create_admin())
