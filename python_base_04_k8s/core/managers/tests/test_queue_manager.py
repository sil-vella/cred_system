import unittest
from unittest.mock import patch, Mock, MagicMock
from core.managers.queue_manager import QueueManager, QueuePriority, QueueStatus
from datetime import datetime
import json

class TestQueueManager(unittest.TestCase):
    def setUp(self):
        self.queue_manager = QueueManager()
        self.queue_manager.redis_manager = Mock()
        self.queue_manager.db_manager = Mock()

    def test_singleton_pattern(self):
        """Test that QueueManager is a singleton."""
        queue_manager2 = QueueManager()
        self.assertIs(self.queue_manager, queue_manager2)

    def test_enqueue_task(self):
        """Test enqueueing a task."""
        # Mock Redis operations
        self.queue_manager.redis_manager.set.return_value = True
        self.queue_manager.redis_manager.zadd.return_value = 1
        
        task_data = {
            'operation': 'insert',
            'collection': 'users',
            'data': {'user_id': 'test123', 'email': 'test@example.com'}
        }
        
        task_id = self.queue_manager.enqueue(
            queue_name='default',
            task_type='user_registration',
            task_data=task_data,
            priority=QueuePriority.NORMAL
        )
        
        # Verify task was stored
        self.queue_manager.redis_manager.set.assert_called_once()
        self.queue_manager.redis_manager.zadd.assert_called_once()
        self.assertIsInstance(task_id, str)

    def test_dequeue_task(self):
        """Test dequeuing a task."""
        # Mock task data
        mock_task = {
            'id': 'test-task-id',
            'queue': 'default',
            'type': 'test_type',
            'data': {'operation': 'insert', 'collection': 'test'},
            'priority': QueuePriority.NORMAL.value,
            'status': QueueStatus.PENDING.value
        }
        
        # Mock Redis operations
        self.queue_manager.redis_manager.zrangebyscore.return_value = ['test-task-id']
        self.queue_manager.redis_manager.zrem.return_value = 1
        self.queue_manager.redis_manager.get.return_value = json.dumps(mock_task)
        self.queue_manager.redis_manager.set.return_value = True
        
        task = self.queue_manager.dequeue('default')
        
        self.assertIsNotNone(task)
        self.assertEqual(task['id'], 'test-task-id')
        self.assertEqual(task['status'], QueueStatus.PROCESSING.value)

    def test_mark_completed(self):
        """Test marking a task as completed."""
        mock_task = {
            'id': 'test-task-id',
            'status': QueueStatus.PROCESSING.value
        }
        
        self.queue_manager.redis_manager.get.return_value = json.dumps(mock_task)
        self.queue_manager.redis_manager.set.return_value = True
        
        result = self.queue_manager.mark_completed('test-task-id', {'result': 'success'})
        
        self.assertTrue(result)
        self.queue_manager.redis_manager.set.assert_called_once()

    def test_mark_failed_with_retry(self):
        """Test marking a task as failed with retry."""
        mock_task = {
            'id': 'test-task-id',
            'queue': 'default',
            'priority': QueuePriority.NORMAL.value,
            'attempts': 0,
            'max_attempts': 3
        }
        
        self.queue_manager.redis_manager.get.return_value = json.dumps(mock_task)
        self.queue_manager.redis_manager.set.return_value = True
        self.queue_manager.redis_manager.zadd.return_value = 1
        
        result = self.queue_manager.mark_failed('test-task-id', 'Test error', retry=True)
        
        self.assertTrue(result)
        # Should be called twice: once for updating task, once for re-adding to queue
        self.assertEqual(self.queue_manager.redis_manager.set.call_count, 1)
        self.queue_manager.redis_manager.zadd.assert_called_once()

    def test_mark_failed_no_retry(self):
        """Test marking a task as failed without retry."""
        mock_task = {
            'id': 'test-task-id',
            'attempts': 2,
            'max_attempts': 3
        }
        
        self.queue_manager.redis_manager.get.return_value = json.dumps(mock_task)
        self.queue_manager.redis_manager.set.return_value = True
        
        result = self.queue_manager.mark_failed('test-task-id', 'Test error', retry=False)
        
        self.assertTrue(result)
        self.queue_manager.redis_manager.set.assert_called_once()

    def test_get_task_status(self):
        """Test getting task status."""
        mock_task = {
            'id': 'test-task-id',
            'status': QueueStatus.COMPLETED.value,
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.queue_manager.redis_manager.get.return_value = json.dumps(mock_task)
        
        status = self.queue_manager.get_task_status('test-task-id')
        
        self.assertIsNotNone(status)
        self.assertEqual(status['id'], 'test-task-id')
        self.assertEqual(status['status'], QueueStatus.COMPLETED.value)

    def test_get_queue_stats(self):
        """Test getting queue statistics."""
        # Mock Redis operations
        self.queue_manager.redis_manager.zcard.return_value = 5
        self.queue_manager.redis_manager.keys.return_value = ['queue:task:1', 'queue:task:2']
        # Use a list that can handle multiple calls
        mock_responses = [
            json.dumps({'queue': 'default', 'status': QueueStatus.PENDING.value}),
            json.dumps({'queue': 'default', 'status': QueueStatus.COMPLETED.value})
        ]
        self.queue_manager.redis_manager.get.side_effect = lambda x: mock_responses.pop(0) if mock_responses else None
        
        stats = self.queue_manager.get_queue_stats()
        
        self.assertIn('default', stats)
        self.assertIn('pending', stats['default'])
        self.assertIn('completed', stats['default'])

    def test_register_handler(self):
        """Test registering a custom task handler."""
        def test_handler(data, db_manager):
            return True
        
        self.queue_manager.register_handler('test_type', test_handler)
        
        self.assertIn('test_type', self.queue_manager.task_handlers)
        self.assertEqual(self.queue_manager.task_handlers['test_type'], test_handler)

    def test_default_task_handler_insert(self):
        """Test default task handler for insert operation."""
        task_data = {
            'operation': 'insert',
            'collection': 'users',
            'data': {'user_id': 'test123', 'email': 'test@example.com'}
        }
        
        self.queue_manager.db_manager.insert.return_value = 'inserted_id'
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertTrue(result)
        self.queue_manager.db_manager.insert.assert_called_once_with('users', task_data['data'])

    def test_default_task_handler_update(self):
        """Test default task handler for update operation."""
        task_data = {
            'operation': 'update',
            'collection': 'users',
            'query': {'user_id': 'test123'},
            'update_data': {'credit_balance': 100}
        }
        
        self.queue_manager.db_manager.update.return_value = 1
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertTrue(result)
        self.queue_manager.db_manager.update.assert_called_once_with('users', task_data['query'], task_data['update_data'])

    def test_default_task_handler_delete(self):
        """Test default task handler for delete operation."""
        task_data = {
            'operation': 'delete',
            'collection': 'users',
            'query': {'user_id': 'test123'}
        }
        
        self.queue_manager.db_manager.delete.return_value = 1
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertTrue(result)
        self.queue_manager.db_manager.delete.assert_called_once_with('users', task_data['query'])

    def test_default_task_handler_find(self):
        """Test default task handler for find operation."""
        task_data = {
            'operation': 'find',
            'collection': 'users',
            'query': {'user_id': 'test123'}
        }
        
        self.queue_manager.db_manager.find.return_value = [{'user_id': 'test123'}]
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertTrue(result)
        self.queue_manager.db_manager.find.assert_called_once_with('users', task_data['query'])

    def test_default_task_handler_unknown_operation(self):
        """Test default task handler with unknown operation."""
        task_data = {
            'operation': 'unknown',
            'collection': 'users',
            'data': {}
        }
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertFalse(result)

    def test_default_task_handler_missing_fields(self):
        """Test default task handler with missing required fields."""
        task_data = {
            'operation': 'insert'
            # Missing collection and data
        }
        
        result = self.queue_manager._default_task_handler('test_type', task_data)
        
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main() 