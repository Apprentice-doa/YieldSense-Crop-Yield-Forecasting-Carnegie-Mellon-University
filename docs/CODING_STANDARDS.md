# Coding Standards

This document outlines the coding standards and best practices for AI/ML projects at Qucoon.

## Python Style Guide

### PEP 8 Compliance
We follow [PEP 8](https://pep8.org/) with the following specifications:
- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Trailing commas**: Required in multi-line structures

### Code Formatting
We use **Black** for automatic code formatting:
```bash
# Format all code
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Import Organization
Use **isort** for import sorting:
```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
import pandas as pd
import torch

# Local imports
from src.models import MyModel
from src.utils import load_data
```

## Type Hints

### Required Type Hints
All public functions must include type hints:
```python
from typing import List, Dict, Optional, Union
import numpy as np

def process_data(
    data: pd.DataFrame, 
    columns: List[str],
    threshold: float = 0.5
) -> pd.DataFrame:
    """Process data with specified columns and threshold."""
    pass

def train_model(
    X: np.ndarray, 
    y: np.ndarray,
    model_config: Optional[Dict[str, Any]] = None
) -> torch.nn.Module:
    """Train model with given data and configuration."""
    pass
```

### Complex Types
```python
from typing import Tuple, Callable, TypeVar

# Type variables
T = TypeVar('T')

# Function types
ProcessorFunc = Callable[[pd.DataFrame], pd.DataFrame]

# Complex return types
def split_data(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split data into train and validation sets."""
    pass
```

## Docstring Requirements

### Google Style Docstrings
All public functions, classes, and modules must have docstrings:

```python
def train_model(X: np.ndarray, y: np.ndarray, epochs: int = 100) -> Dict[str, float]:
    """Train a machine learning model.
    
    Args:
        X: Training features with shape (n_samples, n_features).
        y: Training targets with shape (n_samples,).
        epochs: Number of training epochs.
        
    Returns:
        Dictionary containing training metrics:
            - 'loss': Final training loss
            - 'accuracy': Final training accuracy
            - 'val_loss': Final validation loss
            
    Raises:
        ValueError: If X and y have incompatible shapes.
        RuntimeError: If model fails to converge.
        
    Example:
        >>> X_train = np.random.rand(100, 10)
        >>> y_train = np.random.randint(0, 2, 100)
        >>> metrics = train_model(X_train, y_train, epochs=50)
        >>> print(f"Final accuracy: {metrics['accuracy']:.3f}")
    """
    pass
```

### Class Docstrings
```python
class ModelTrainer:
    """Handles model training and evaluation.
    
    This class provides a unified interface for training various ML models
    with consistent logging, checkpointing, and evaluation.
    
    Attributes:
        model: The ML model to train.
        optimizer: Optimization algorithm.
        device: Computing device (CPU/GPU).
        
    Example:
        >>> trainer = ModelTrainer(model, optimizer)
        >>> trainer.train(train_loader, val_loader, epochs=10)
    """
    
    def __init__(self, model: torch.nn.Module, optimizer: torch.optim.Optimizer):
        """Initialize trainer with model and optimizer."""
        pass
```

## ML-Specific Standards

### Experiment Tracking
All experiments must be tracked with metadata:
```python
import mlflow

def train_with_tracking(config: Dict[str, Any]) -> None:
    """Train model with MLflow tracking."""
    with mlflow.start_run():
        # Log parameters
        mlflow.log_params(config)
        
        # Train model
        model = create_model(config)
        metrics = train_model(model, config)
        
        # Log metrics
        mlflow.log_metrics(metrics)
        
        # Log model
        mlflow.pytorch.log_model(model, "model")
```

### Model Versioning
```python
from datetime import datetime

def save_model(model: torch.nn.Module, metrics: Dict[str, float]) -> str:
    """Save model with version information."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version = f"v1.0.0_{timestamp}"
    
    model_path = f"models/{model.__class__.__name__}_{version}.pt"
    
    # Save with metadata
    torch.save({
        'model_state_dict': model.state_dict(),
        'metrics': metrics,
        'version': version,
        'timestamp': timestamp
    }, model_path)
    
    return model_path
```

### Data Validation
```python
import pandas as pd
from typing import List

def validate_dataframe(
    df: pd.DataFrame, 
    required_columns: List[str],
    numeric_columns: List[str]
) -> None:
    """Validate DataFrame structure and content.
    
    Args:
        df: DataFrame to validate.
        required_columns: Columns that must be present.
        numeric_columns: Columns that must be numeric.
        
    Raises:
        ValueError: If validation fails.
    """
    # Check required columns
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check numeric columns
    for col in numeric_columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Column {col} must be numeric")
```

## Code Review Checklist

### Before Submitting PR
- [ ] Code follows PEP 8 and Black formatting
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] Tests are written and passing
- [ ] No hardcoded values (use config files)
- [ ] Error handling is implemented
- [ ] Logging is appropriate
- [ ] No sensitive data in code

### Code Quality Checks
- [ ] Functions are small and focused (< 50 lines)
- [ ] No code duplication
- [ ] Meaningful variable and function names
- [ ] Proper exception handling
- [ ] Resource cleanup (file handles, connections)
- [ ] Thread safety considered if applicable

### ML-Specific Checks
- [ ] Experiments are tracked with MLflow/W&B
- [ ] Model artifacts are versioned
- [ ] Data validation is implemented
- [ ] Reproducibility is ensured (random seeds)
- [ ] Memory usage is optimized
- [ ] GPU resources are properly managed

## Linting Configuration

### flake8 Configuration (.flake8)
```ini
[flake8]
max-line-length = 88
extend-ignore = E203, W503
exclude = 
    .git,
    __pycache__,
    .venv,
    venv,
    build,
    dist
```

### mypy Configuration (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Error Handling

### Exception Handling
```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def load_model(model_path: str) -> Optional[torch.nn.Module]:
    """Load model with proper error handling."""
    try:
        model = torch.load(model_path)
        logger.info(f"Successfully loaded model from {model_path}")
        return model
    except FileNotFoundError:
        logger.error(f"Model file not found: {model_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise
```

### Custom Exceptions
```python
class ModelTrainingError(Exception):
    """Raised when model training fails."""
    pass

class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass
```

## Performance Guidelines

### Memory Management
```python
import gc
import torch

def train_epoch(model, dataloader):
    """Train one epoch with memory management."""
    for batch in dataloader:
        # Forward pass
        output = model(batch)
        loss = compute_loss(output, batch.labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        
        # Clear cache periodically
        if batch_idx % 100 == 0:
            torch.cuda.empty_cache()
            gc.collect()
```

### Efficient Data Processing
```python
# Use vectorized operations
def process_features(df: pd.DataFrame) -> pd.DataFrame:
    """Process features efficiently."""
    # Good: vectorized operation
    df['normalized'] = (df['value'] - df['value'].mean()) / df['value'].std()
    
    # Avoid: iterating over rows
    # for idx, row in df.iterrows():  # Don't do this
    #     df.loc[idx, 'normalized'] = (row['value'] - mean) / std
    
    return df
```

## Security Guidelines

### Sensitive Data
```python
import os
from pathlib import Path

# Good: Use environment variables
API_KEY = os.getenv('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable not set")

# Good: Use secure file paths
MODEL_PATH = Path(os.getenv('MODEL_PATH', './models'))

# Bad: Hardcoded secrets
# API_KEY = "sk-1234567890abcdef"  # Never do this
```

### Input Validation
```python
def predict(model: torch.nn.Module, input_data: str) -> Dict[str, float]:
    """Make prediction with input validation."""
    # Validate input
    if not input_data or len(input_data) > 10000:
        raise ValueError("Invalid input data")
    
    # Sanitize input
    cleaned_input = sanitize_text(input_data)
    
    # Make prediction
    return model.predict(cleaned_input)
```