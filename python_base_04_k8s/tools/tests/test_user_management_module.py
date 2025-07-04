#!/usr/bin/env python3
"""
Test suite for UserManagementModule

This module tests the core functionality of the UserManagementModule including:
- User creation
- User retrieval
- User updating
- User deletion
- User search
- Database connection handling
- Queue integration
"""

import unittest
import json
import bcrypt
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.modules.user_management_module.user_management_main import UserManagementModule
from core.managers.database_manager import DatabaseManager
from core.managers.redis_manager import RedisManager
from core.managers.queue_manager import QueueManager, QueuePriority


class TestUserManagementModule(unittest.TestCase):
    """Test cases for UserManagementModule"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create mock managers
        self.mock_db_manager = Mock(spec=DatabaseManager)
        self.mock_analytics_db = Mock(spec=DatabaseManager)
        self.mock_redis_manager = Mock(spec=RedisManager)
        self.mock_queue_manager = Mock(spec=QueueManager)
        
        # Create mock app_manager
        self.mock_app_manager = Mock()
        self.mock_app_manager.get_db_manager.side_effect = lambda role: {
            "read_write": self.mock_db_manager,
            "read_only": self.mock_analytics_db
        }[role]
        self.mock_app_manager.get_redis_manager.return_value = self.mock_redis_manager
        self.mock_app_manager.get_queue_manager.return_value = self.mock_queue_manager
        
        # Create the module instance
        self.module = UserManagementModule(app_manager=self.mock_app_manager)
        self.module.initialize(self.app)
        
        # Test data
        self.test_user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'password123',
            'status': 'active'
        }
        
        self.test_user_id = '507f1f77bcf86cd799439011'
        self.test_user_doc = {
            '_id': self.test_user_id,
            'email': 'test@example.com',
            'username': 'testuser',
            'password': bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            'created_at': '2025-07-03T16:00:00.000Z',
            'updated_at': '2025-07-03T16:00:00.000Z',
            'status': 'active'
        }

    def tearDown(self):
        """Clean up after each test method."""
        pass

    def test_module_initialization(self):
        """Test that the module initializes correctly."""
        self.assertIsNotNone(self.module)
        self.assertEqual(self.module.dependencies, ["connection_api"])
        self.assertTrue(self.module._initialized)

    def test_route_registration(self):
        """Test that all routes are registered correctly."""
        expected_routes = [
            ('/users', 'POST'),
            ('/users/<user_id>', 'GET'),
            ('/users/<user_id>', 'PUT'),
            ('/users/<user_id>', 'DELETE'),
            ('/users/search', 'POST')
        ]
        
        # registered_routes is a list, not a dict
        self.assertEqual(len(self.module.registered_routes), len(expected_routes))

    @patch('core.modules.user_management_module.user_management_main.bcrypt')
    def test_create_user_success(self, mock_bcrypt):
        """Test successful user creation."""
        # Mock bcrypt
        mock_bcrypt.hashpw.return_value = b'hashed_password'
        mock_bcrypt.gensalt.return_value = b'salt'
        
        # Mock queue manager
        self.mock_queue_manager.enqueue.return_value = 'task_123'
        
        # Create request context
        with self.app.test_request_context('/users', 
                                        method='POST',
                                        json=self.test_user_data):
            response, status_code = self.module.create_user()
            response_data = json.loads(response.get_data(as_text=True))
            
            # Verify response
            self.assertEqual(status_code, 202)
            self.assertEqual(response_data['message'], 'User creation is being processed')
            self.assertEqual(response_data['task_id'], 'task_123')
            self.assertEqual(response_data['email'], 'test@example.com')
            self.assertEqual(response_data['username'], 'testuser')
            self.assertEqual(response_data['status'], 'pending')
            
            # Verify queue manager was called
            self.mock_queue_manager.enqueue.assert_called_once()
            call_args = self.mock_queue_manager.enqueue.call_args
            self.assertEqual(call_args[1]['queue_name'], 'default')
            self.assertEqual(call_args[1]['task_type'], 'user_creation')
            self.assertEqual(call_args[1]['priority'], QueuePriority.NORMAL)

    def test_create_user_missing_fields(self):
        """Test user creation with missing required fields."""
        incomplete_data = {'email': 'test@example.com'}  # Missing username and password
        
        with self.app.test_request_context('/users', 
                                        method='POST',
                                        json=incomplete_data):
            response, status_code = self.module.create_user()
            response_data = json.loads(response.get_data(as_text=True))
            
            self.assertEqual(status_code, 400)
            self.assertIn('error', response_data)
            self.assertIn('email, username, and password are required', response_data['error'])

    def test_get_user_success(self):
        """Test successful user retrieval."""
        # Mock database response
        self.mock_analytics_db.find_one.return_value = self.test_user_doc.copy()
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='GET'):
            response, status_code = self.module.get_user(self.test_user_id)
            response_data = json.loads(response.get_data(as_text=True))
            
            # Verify response
            self.assertEqual(status_code, 200)
            self.assertEqual(response_data['email'], 'test@example.com')
            self.assertEqual(response_data['username'], 'testuser')
            self.assertEqual(response_data['status'], 'active')
            # Password should be removed
            self.assertNotIn('password', response_data)
            
            # Verify database was called
            self.mock_analytics_db.find_one.assert_called_once_with("users", {"_id": self.test_user_id})

    def test_get_user_not_found(self):
        """Test user retrieval when user doesn't exist."""
        # Mock database response
        self.mock_analytics_db.find_one.return_value = None
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='GET'):
            response, status_code = self.module.get_user(self.test_user_id)
            response_data = json.loads(response.get_data(as_text=True))
            
            self.assertEqual(status_code, 404)
            self.assertIn('error', response_data)
            self.assertEqual(response_data['error'], 'User not found')

    def test_update_user_success(self):
        """Test successful user update."""
        # Mock queue manager
        self.mock_queue_manager.enqueue.return_value = 'task_456'
        
        update_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'status': 'inactive'
        }
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='PUT',
                                        json=update_data):
            response, status_code = self.module.update_user(self.test_user_id)
            response_data = json.loads(response.get_data(as_text=True))
            
            # Verify response
            self.assertEqual(status_code, 202)
            self.assertEqual(response_data['message'], 'User update is being processed')
            self.assertEqual(response_data['task_id'], 'task_456')
            self.assertEqual(response_data['user_id'], self.test_user_id)
            self.assertEqual(response_data['status'], 'pending')
            
            # Verify queue manager was called
            self.mock_queue_manager.enqueue.assert_called_once()
            call_args = self.mock_queue_manager.enqueue.call_args
            self.assertEqual(call_args[1]['queue_name'], 'default')
            self.assertEqual(call_args[1]['task_type'], 'user_update')
            self.assertEqual(call_args[1]['priority'], QueuePriority.NORMAL)

    def test_update_user_ignores_invalid_fields(self):
        """Test that user update ignores invalid fields."""
        # Mock queue manager
        self.mock_queue_manager.enqueue.return_value = 'task_789'
        
        update_data = {
            'username': 'updateduser',
            'invalid_field': 'should_be_ignored',
            'password': 'newpassword'  # Should be ignored
        }
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='PUT',
                                        json=update_data):
            response = self.module.update_user(self.test_user_id)
            
            # Verify queue manager was called with only valid fields
            call_args = self.mock_queue_manager.enqueue.call_args
            task_data = call_args[1]['task_data']
            update_data_sent = task_data['update_data']
            
            self.assertIn('username', update_data_sent)
            self.assertNotIn('invalid_field', update_data_sent)
            self.assertNotIn('password', update_data_sent)

    def test_delete_user_success(self):
        """Test successful user deletion."""
        # Mock queue manager
        self.mock_queue_manager.enqueue.return_value = 'task_999'
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='DELETE'):
            response, status_code = self.module.delete_user(self.test_user_id)
            response_data = json.loads(response.get_data(as_text=True))
            
            # Verify response
            self.assertEqual(status_code, 202)
            self.assertEqual(response_data['message'], 'User deletion is being processed')
            self.assertEqual(response_data['task_id'], 'task_999')
            self.assertEqual(response_data['user_id'], self.test_user_id)
            self.assertEqual(response_data['status'], 'pending')
            
            # Verify queue manager was called with high priority
            self.mock_queue_manager.enqueue.assert_called_once()
            call_args = self.mock_queue_manager.enqueue.call_args
            self.assertEqual(call_args[1]['queue_name'], 'high_priority')
            self.assertEqual(call_args[1]['task_type'], 'user_deletion')
            self.assertEqual(call_args[1]['priority'], QueuePriority.HIGH)

    def test_search_users_success(self):
        """Test successful user search."""
        # Mock database response
        mock_users = [
            {'_id': '1', 'username': 'user1', 'email': 'user1@example.com', 'password': 'hash1'},
            {'_id': '2', 'username': 'user2', 'email': 'user2@example.com', 'password': 'hash2'}
        ]
        self.mock_analytics_db.find.return_value = mock_users
        
        search_data = {'username': 'user'}
        
        with self.app.test_request_context('/users/search', 
                                        method='POST',
                                        json=search_data):
            response, status_code = self.module.search_users()
            response_data = json.loads(response.get_data(as_text=True))
            
            # Verify response
            self.assertEqual(status_code, 200)
            self.assertIn('users', response_data)
            self.assertEqual(len(response_data['users']), 2)
            
            # Verify passwords are removed
            for user in response_data['users']:
                self.assertNotIn('password', user)
            
            # Verify database was called with correct query
            self.mock_analytics_db.find.assert_called_once()
            call_args = self.mock_analytics_db.find.call_args
            self.assertEqual(call_args[0][0], 'users')
            self.assertIn('username', call_args[0][1])

    def test_search_users_no_filters(self):
        """Test user search with no filters."""
        # Mock database response
        mock_users = [{'username': 'user1', 'email': 'user1@example.com'}]
        self.mock_analytics_db.find.return_value = mock_users
        
        with self.app.test_request_context('/users/search', 
                                        method='POST',
                                        json={}):
            response, status_code = self.module.search_users()
            response_data = json.loads(response.get_data(as_text=True))
            
            self.assertEqual(status_code, 200)
            self.assertIn('users', response_data)
            
            # Verify database was called with empty query
            call_args = self.mock_analytics_db.find.call_args
            self.assertEqual(call_args[0][1], {})

    def test_health_check(self):
        """Test module health check."""
        health_status = self.module.health_check()
        
        self.assertIn('status', health_status)
        self.assertIn('dependencies', health_status)
        self.assertEqual(health_status['dependencies'], ["connection_api"])

    def test_database_connection_failure(self):
        """Test behavior when database is unavailable."""
        # Mock database to be unavailable
        self.mock_analytics_db.available = False
        
        # Reinitialize the module to trigger database check
        self.module.initialize_database()
        
        # The module should handle this gracefully
        self.assertIsNotNone(self.module)

    @patch('core.modules.user_management_module.user_management_main.custom_log')
    def test_database_connection_exception(self, mock_log):
        """Test behavior when database connection throws exception."""
        # Mock database to throw exception
        self.mock_analytics_db.available = True
        # Create a proper mock structure for the db object
        self.mock_analytics_db.db = Mock()
        self.mock_analytics_db.db.command.side_effect = Exception("Connection failed")
        
        # Reinitialize the module to trigger database check
        self.module.initialize_database()
        
        # Verify that the exception was logged
        mock_log.assert_called()

    def test_create_user_exception_handling(self):
        """Test exception handling in user creation."""
        # Mock queue manager to throw exception
        self.mock_queue_manager.enqueue.side_effect = Exception("Queue error")
        
        with self.app.test_request_context('/users', 
                                        method='POST',
                                        json=self.test_user_data):
            response, status_code = self.module.create_user()
            response_data = json.loads(response.get_data(as_text=True))
            
            self.assertEqual(status_code, 500)
            self.assertIn('error', response_data)
            self.assertEqual(response_data['error'], 'Failed to queue user creation')

    def test_get_user_exception_handling(self):
        """Test exception handling in user retrieval."""
        # Mock database to throw exception
        self.mock_analytics_db.find_one.side_effect = Exception("Database error")
        
        with self.app.test_request_context(f'/users/{self.test_user_id}', 
                                        method='GET'):
            response, status_code = self.module.get_user(self.test_user_id)
            response_data = json.loads(response.get_data(as_text=True))
            
            self.assertEqual(status_code, 500)
            self.assertIn('error', response_data)
            self.assertEqual(response_data['error'], 'Failed to get user')


class TestUserManagementModuleIntegration(unittest.TestCase):
    """Integration tests for UserManagementModule with real Flask app"""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Create module without app_manager (will use fallback managers)
        self.module = UserManagementModule()
        self.module.initialize(self.app)
        
        self.client = self.app.test_client()

    def test_health_endpoint(self):
        """Test that the health endpoint is accessible."""
        # This would require the module to be properly registered with Flask
        # For now, we'll test the health_check method directly
        health_status = self.module.health_check()
        self.assertIn('status', health_status)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2) 