import pytest
from fastapi import status

from conftest import event_in_db, get_event_by_id
from factories import EventPayloadFactory, EventFactory, TicketFactory

BASE_URL = '/api/v1/events/'

@pytest.mark.asyncio
class TestEventPost:

    @pytest.fixture
    async def event_payload(self):
        return EventPayloadFactory.build()

    async def test_post_event_by_superuser(self, authorized_superuser, db_connection, event_payload, get_event_by_id):
        event_dict = event_payload.model_dump(mode='json')

        response = await authorized_superuser.post(BASE_URL, json = event_dict)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data['title'] == event_payload.title
        assert data['tickets_quantity'] == event_payload.tickets_quantity

        found_event = await get_event_by_id(data['id'])

        assert found_event is not None
        assert found_event.title == event_payload.title
        assert found_event.tickets_quantity == event_payload.tickets_quantity

    async def test_post_event_by_normal_user(self, authorized_user, db_connection, event_payload, get_event_by_title):
        event_dict = event_payload.model_dump(mode='json')

        response = await authorized_user.post(BASE_URL, json = event_dict)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        db_event = await get_event_by_title(event_payload.title)
        assert db_event is None

    async def test_post_event_by_unauthorized_client(self, client, db_connection, event_payload, get_event_by_title):
        event_dict = event_payload.model_dump(mode='json')

        response = await client.post(BASE_URL, json=event_dict)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        db_event = await get_event_by_title(event_payload.title)
        assert db_event is None

    async def test_post_event_with_negative_ticket_quantity(self, authorized_superuser, event_payload):
        event_dict = event_payload.model_dump(mode='json')
        event_dict['tickets_quantity'] = -10

        response = await authorized_superuser.post(BASE_URL, json = event_dict)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        error_detail = response.json()
        assert any(err['loc'][-1] == 'tickets_quantity' for err in error_detail['detail'])

@pytest.mark.asyncio
class TestEventGet:

    async def test_get_all_events(self, client, db_connection):
        factory_events = EventFactory.batch(10)

        db_connection.add_all(factory_events)
        await db_connection.commit()

        response = await client.get(BASE_URL)

        assert response.status_code == status.HTTP_200_OK
        response_events = response.json()
        assert isinstance(response_events, list)
        assert len(response_events) == 10

        returned_events = sorted([item['id'] for item in response_events])
        created_events = sorted([e.id for e in factory_events])

        assert returned_events == created_events

    async def test_get_one_event(self, client, event_in_db):
        response = await client.get(f'{BASE_URL}{event_in_db.id}')

        assert response.status_code == status.HTTP_200_OK
        event = response.json()
        assert event['title'] == event_in_db.title
        assert event['tickets_quantity'] == event_in_db.tickets_quantity

    async def test_get_non_existent_event(self, client):
        response = await client.get(f'{BASE_URL}999')

        assert response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
class TestEventPagination:
    async def test_event_pagination(self, client, db_connection):
        factory_events = EventFactory.batch(10)
        db_connection.add_all(factory_events)
        await db_connection.commit()

        response_p1 = await client.get(f'{BASE_URL}?limit=5&offset=0')

        assert response_p1.status_code == status.HTTP_200_OK
        events_p1 = response_p1.json()
        assert len(events_p1) == 5

        response_p2 = await client.get(f'{BASE_URL}?limit=5&offset=5')

        assert response_p2.status_code == status.HTTP_200_OK
        events_p2 = response_p2.json()
        assert len(events_p2) == 5

        response_p3 = await client.get(f'{BASE_URL}?limit=5&offset=10')

        assert response_p3.status_code == status.HTTP_200_OK
        events_p3 = response_p3.json()
        assert len(events_p3) == 0
        assert isinstance(events_p3, list)

@pytest.mark.asyncio
class TestEventPatch:

    async def test_patch_event_by_superuser(self, authorized_superuser, db_connection, event_in_db, get_event_by_id):
        orig_id = event_in_db.id
        orig_tickets_quantity = event_in_db.tickets_quantity
        payload = {
            'title' : 'New Title'
        }

        response = await authorized_superuser.patch(f'{BASE_URL}{event_in_db.id}', json=payload)
        assert response.status_code == status.HTTP_200_OK

        db_connection.expire_all()

        updated_event = await get_event_by_id(orig_id)

        assert updated_event.title == payload.get('title')
        assert updated_event.tickets_quantity == orig_tickets_quantity

    async def test_patch_event_by_normal_user(self, authorized_user, db_connection, event_in_db, get_event_by_id):
        orig_title = event_in_db.title
        payload = {
            'title' : 'New Title'
        }

        response = await authorized_user.patch(f'{BASE_URL}{event_in_db.id}', json=payload)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        db_event = await get_event_by_id(event_in_db.id)

        assert db_event.title == orig_title
        assert db_event.title != payload.get('title')


    async def test_patch_event_by_unauthorized_client(self, client, db_connection, event_in_db, get_event_by_id):
        original_title = event_in_db.title
        payload = {
            'title' : 'New Title'
        }

        response = await client.patch(f'{BASE_URL}{event_in_db.id}', json=payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        db_event = await get_event_by_id(event_in_db.id)

        assert db_event.title == original_title
        assert db_event.title != payload.get('title')

    async def test_patch_non_existent_event(self, authorized_superuser, get_event_by_id):
        non_existent = 999
        payload = {
            'title': 'New Title'
        }

        response = await authorized_superuser.patch(f'{BASE_URL}{non_existent}', json=payload)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        db_event = await get_event_by_id(non_existent)
        assert db_event is None

@pytest.mark.asyncio
class TestEventDelete:

    async def test_delete_event_by_superuser(self, authorized_superuser, db_connection, event_in_db, get_event_by_id):
        event_id = event_in_db.id
        
        response = await authorized_superuser.delete(f'{BASE_URL}{event_id}')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        db_event = await get_event_by_id(event_id)
        assert db_event is None

    async def test_delete_event_by_normal_user(self, authorized_user, db_connection, event_in_db, get_event_by_id):
        event_id = event_in_db.id

        response = await authorized_user.delete(f'{BASE_URL}{event_id}')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        db_event = await get_event_by_id(event_id)
        assert db_event is not None

    async def test_delete_event_by_unauthorized_user(self, client, db_connection, event_in_db, get_event_by_id):
        event_id = event_in_db.id

        response = await client.delete(f'{BASE_URL}{event_id}')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        db_event = await get_event_by_id(event_id)
        assert db_event is not None

    async def test_delete_event_with_tickets(self, authorized_superuser, db_connection, event_in_db, get_event_by_id):
        ticket = TicketFactory.build(event=event_in_db)

        db_connection.add(ticket)
        await db_connection.commit()

        response = await authorized_superuser.delete(f'{BASE_URL}{event_in_db.id}')
        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_delete_non_existent_event(self, authorized_superuser, db_connection, get_event_by_id):
        non_existent = 999

        response = await  authorized_superuser.delete(f'{BASE_URL}{non_existent}')
        assert response.status_code == status.HTTP_404_NOT_FOUND

        db_event = await get_event_by_id(non_existent)
        assert db_event is None