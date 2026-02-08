import pytest
from fastapi import status
from sqlalchemy import select

from src.models import User


@pytest.mark.pytest
async def test_successful_signup(client, db_connection):
    payload = {
        'email' : '123@gmail.com',
        'password' : 'very_secure_password'
    }

    response = await client.post('/api/v1/auth/signup', json=payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data['email'] == payload['email']
    assert 'id' in data
    assert 'password' not in data
    assert 'hashed_password' not in data

    query = select(User).where(User.email == payload['email'])
    result = await db_connection.execute(query)
    created_user = result.scalar_one_or_none()

    assert created_user is not None
    assert created_user.is_active is True
    assert created_user.is_superuser is False

    assert created_user.hashed_password != payload['password']
    assert created_user.hashed_password.startswith('$argon2')

@pytest.mark.asyncio
async def test_email_duplicate(client, normal_user):
    payload = {
        'email' : normal_user.email,
        'password' : 'very_secure_password'
    }

    response = await client.post('/api/v1/auth/signup', json=payload)
    assert response.status_code == status.HTTP_409_CONFLICT

    data = response.json()
    assert 'detail' in data

@pytest.mark.asyncio
async def test_successful_login(client, normal_user):
    payload = {
        'username' : normal_user.email,
        'password' : 'very_secure_password'
    }
    response = await client.post('/api/v1/auth/login', data=payload)

    assert response.status_code == status.HTTP_200_OK
    token_data = response.json()
    assert 'access_token' in token_data
    assert token_data['token_type'] == 'bearer'

@pytest.mark.asyncio
async def test_wrong_password(client, normal_user):
    payload = {
        'username' : normal_user.email,
        'password' : 'very_secure_password1'
    }

    response = await client.post('/api/v1/auth/login', data=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.asyncio
async def test_wrong_login(client, normal_user):
    payload = {
        'username': 'wrong.email@wrong.email',
        'password': 'very_secure_password'
    }

    response = await client.post('/api/v1/auth/login', data=payload)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED