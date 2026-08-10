"""Example test file demonstrating testing structure and best practices."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch


class TestDataProcessing:
    """Test data processing functions."""
    
    def test_data_loading(self):
        """Test data loading functionality."""
        # Create sample data
        sample_data = pd.DataFrame({
            'text': ['Hello world', 'Test message', 'Another example'],
            'label': [1, 0, 1]
        })
        
        # Test basic properties
        assert len(sample_data) == 3
        assert 'text' in sample_data.columns
        assert 'label' in sample_data.columns
        assert sample_data['label'].dtype == 'int64'
    
    def test_data_validation(self):
        """Test data validation functions."""
        # Valid data
        valid_data = pd.DataFrame({
            'text': ['Sample text'],
            'label': [1]
        })
        
        # Test validation passes
        assert not valid_data.empty
        assert valid_data['text'].notna().all()
        assert valid_data['label'].notna().all()
    
    def test_data_preprocessing(self):
        """Test data preprocessing pipeline."""
        # Sample data with issues
        raw_data = pd.DataFrame({
            'text': ['  Hello World  ', 'TEST MESSAGE', None, ''],
            'label': [1, 0, 1, 0]
        })
        
        # Basic preprocessing
        processed_data = raw_data.copy()
        processed_data['text'] = processed_data['text'].fillna('')
        processed_data['text'] = processed_data['text'].str.strip().str.lower()
        
        # Assertions
        assert processed_data['text'].iloc[0] == 'hello world'
        assert processed_data['text'].iloc[1] == 'test message'
        assert processed_data['text'].iloc[2] == ''


class TestModelFunctions:
    """Test model-related functions."""
    
    def test_model_initialization(self):
        """Test model initialization."""
        # Mock model configuration
        config = {
            'model_type': 'test_model',
            'num_classes': 2,
            'hidden_size': 128
        }
        
        # Test configuration validation
        assert config['num_classes'] > 0
        assert config['hidden_size'] > 0
        assert isinstance(config['model_type'], str)
    
    @pytest.mark.parametrize("input_size,expected_output", [
        (10, 2),
        (50, 2),
        (100, 2),
    ])
    def test_model_output_shape(self, input_size, expected_output):
        """Test model output shapes with different input sizes."""
        # Mock input
        mock_input = np.random.rand(1, input_size)
        
        # Mock model prediction
        mock_output = np.random.rand(1, expected_output)
        
        # Test output shape
        assert mock_output.shape == (1, expected_output)
    
    def test_model_training_step(self):
        """Test single training step."""
        # Mock training data
        X_batch = np.random.rand(32, 10)
        y_batch = np.random.randint(0, 2, 32)
        
        # Mock training step
        loss = np.random.rand()  # Mock loss value
        
        # Assertions
        assert X_batch.shape[0] == y_batch.shape[0]  # Batch sizes match
        assert loss >= 0  # Loss should be non-negative
        assert isinstance(loss, (int, float, np.number))


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_set_random_seed(self):
        """Test random seed setting for reproducibility."""
        seed = 42
        
        # Set seed and generate random numbers
        np.random.seed(seed)
        random_nums_1 = np.random.rand(5)
        
        # Reset seed and generate again
        np.random.seed(seed)
        random_nums_2 = np.random.rand(5)
        
        # Should be identical
        np.testing.assert_array_equal(random_nums_1, random_nums_2)
    
    def test_config_loading(self):
        """Test configuration loading."""
        # Mock configuration
        config = {
            'model': {
                'type': 'bert',
                'num_classes': 2
            },
            'training': {
                'learning_rate': 2e-5,
                'batch_size': 16
            }
        }
        
        # Test configuration structure
        assert 'model' in config
        assert 'training' in config
        assert config['model']['num_classes'] == 2
        assert config['training']['batch_size'] > 0
    
    def test_metrics_calculation(self):
        """Test metrics calculation functions."""
        # Mock predictions and labels
        y_true = np.array([1, 0, 1, 1, 0])
        y_pred = np.array([1, 0, 1, 0, 0])
        
        # Calculate accuracy manually
        accuracy = np.mean(y_true == y_pred)
        
        # Test accuracy calculation
        assert 0 <= accuracy <= 1
        assert accuracy == 0.8  # 4 out of 5 correct


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline from data to prediction."""
        # Mock data
        data = pd.DataFrame({
            'text': ['positive example', 'negative example'],
            'label': [1, 0]
        })
        
        # Mock preprocessing
        processed_data = data.copy()
        processed_data['text_length'] = processed_data['text'].str.len()
        
        # Mock model prediction
        predictions = np.array([1, 0])
        
        # Test pipeline
        assert len(predictions) == len(data)
        assert all(pred in [0, 1] for pred in predictions)
    
    @pytest.mark.slow
    def test_model_training_integration(self):
        """Test model training integration (marked as slow)."""
        # This would be a longer integration test
        # Mock training loop
        epochs = 2
        losses = []
        
        for epoch in range(epochs):
            # Mock epoch training
            epoch_loss = 1.0 / (epoch + 1)  # Decreasing loss
            losses.append(epoch_loss)
        
        # Test training progress
        assert len(losses) == epochs
        assert losses[0] > losses[-1]  # Loss should decrease


# Fixtures for common test data
@pytest.fixture
def sample_dataframe():
    """Fixture providing sample DataFrame for tests."""
    return pd.DataFrame({
        'text': ['Hello world', 'Test message', 'Another example'],
        'label': [1, 0, 1],
        'id': [1, 2, 3]
    })


@pytest.fixture
def mock_model():
    """Fixture providing mock model for tests."""
    model = Mock()
    model.predict.return_value = np.array([1, 0, 1])
    model.predict_proba.return_value = np.array([[0.2, 0.8], [0.9, 0.1], [0.3, 0.7]])
    return model


def test_with_fixture(sample_dataframe):
    """Test using fixture data."""
    assert len(sample_dataframe) == 3
    assert 'text' in sample_dataframe.columns


def test_with_mock_model(mock_model):
    """Test using mock model fixture."""
    predictions = mock_model.predict([1, 2, 3])
    assert len(predictions) == 3
    assert all(pred in [0, 1] for pred in predictions)