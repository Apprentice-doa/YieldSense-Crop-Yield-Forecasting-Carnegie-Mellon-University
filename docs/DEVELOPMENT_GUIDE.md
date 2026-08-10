# Development Guide

This guide covers the local development workflow, testing procedures, and debugging guidelines for AI/ML projects.

## Local Development Setup

### Quick Start
```bash
# Clone and setup
git clone <repo-url>
cd <project-name>
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### Development Environment
```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional but recommended)
pre-commit install

# Start Jupyter Lab for notebook development
jupyter lab

# Start MLflow UI for experiment tracking
mlflow ui
```

## Running the Project

### Training Models
```bash
# Run training script
python src/train.py --config configs/train_config.yaml

# With specific parameters
python src/train.py --model-type transformer --epochs 10
```

### Running Inference
```bash
# Batch inference
python src/predict.py --input data/test.csv --output results/predictions.csv

# Single prediction
python src/predict.py --text "example input"
```

### Data Processing
```bash
# Process raw data
python scripts/process_data.py --input data/raw/ --output data/processed/

# Validate data quality
python scripts/validate_data.py --data data/processed/
```

## Testing Procedures

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_model.py

# Run tests with specific markers
pytest -m "not slow"
```

### Test Categories
- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **Model tests**: Test model training and inference
- **Data tests**: Validate data quality and schemas

### Writing Tests
```python
# Example test structure
def test_model_training():
    """Test model training with sample data."""
    model = MyModel()
    X_train, y_train = load_sample_data()
    
    model.fit(X_train, y_train)
    
    assert model.is_fitted
    assert model.score(X_train, y_train) > 0.8
```

## Code Quality Checks

### Formatting and Linting
```bash
# Format code with Black
black src/ tests/

# Check formatting
black --check src/ tests/

# Run flake8 linting
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Debugging Guidelines

### Common Debugging Tools
```python
# Use debugger
import pdb; pdb.set_trace()

# Or with ipdb for better interface
import ipdb; ipdb.set_trace()

# Logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

### Model Debugging
```python
# Check model architecture
print(model.summary())

# Visualize training metrics
import matplotlib.pyplot as plt
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])

# Check data shapes
print(f"Input shape: {X.shape}")
print(f"Output shape: {y.shape}")
```

### Performance Profiling
```bash
# Profile Python code
python -m cProfile -o profile.stats src/train.py

# Memory profiling
pip install memory-profiler
python -m memory_profiler src/train.py
```

## Docker Development

### Building Container
```bash
# Build development image
docker build -t project-dev .

# Run container with volume mounting
docker run -v $(pwd):/app -p 8888:8888 project-dev
```

### Docker Compose (if applicable)
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## CI/CD Pipeline

### GitHub Actions Workflow
The CI pipeline runs on every push and PR:
1. **Linting**: Black, flake8, mypy
2. **Testing**: pytest with coverage
3. **Security**: Safety check for vulnerabilities
4. **Documentation**: Build and validate docs

### Local CI Simulation
```bash
# Run the same checks as CI
./scripts/run_ci_checks.sh
```

## Troubleshooting

### Common Issues

#### Environment Issues
```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

#### CUDA/GPU Issues
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"

# Check GPU memory
nvidia-smi
```

#### Memory Issues
```bash
# Monitor memory usage
htop

# Clear Python cache
python -c "import gc; gc.collect()"
```

#### Data Loading Issues
```bash
# Check file permissions
ls -la data/

# Verify data integrity
python scripts/validate_data.py
```

### Getting Help
1. Check error logs in `logs/`
2. Search existing issues on GitHub
3. Ask in team chat channel
4. Create detailed issue with reproduction steps

## Performance Optimization

### Code Optimization
- Use vectorized operations (NumPy, Pandas)
- Profile bottlenecks with cProfile
- Consider multiprocessing for CPU-bound tasks
- Use appropriate data types (float32 vs float64)

### Model Optimization
- Batch processing for inference
- Model quantization for deployment
- Use mixed precision training
- Implement early stopping

### Data Pipeline Optimization
- Use efficient data formats (Parquet, HDF5)
- Implement data caching
- Parallel data loading
- Streaming for large datasets

## Best Practices

### Development Workflow
1. **Start small**: Begin with simple baseline
2. **Iterate quickly**: Make small, testable changes
3. **Document experiments**: Use MLflow/W&B
4. **Version everything**: Code, data, models
5. **Test continuously**: Write tests as you develop

### Code Organization
- Keep functions small and focused
- Use type hints consistently
- Write docstrings for all public functions
- Separate configuration from code
- Use meaningful variable names

### Experiment Management
- Track all experiments with metadata
- Save model checkpoints regularly
- Document hyperparameter choices
- Compare results systematically
- Archive successful experiments