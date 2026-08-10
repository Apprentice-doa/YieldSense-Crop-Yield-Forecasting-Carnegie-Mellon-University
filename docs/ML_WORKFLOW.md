# ML Workflow

This document outlines the machine learning workflow, experiment tracking, model training, evaluation, and deployment practices.

## Experiment Tracking Setup

### **[CUSTOMIZE]** Choose your experiment tracking tool:

### Option 1: MLflow
```python
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

# Initialize MLflow
mlflow.set_tracking_uri("http://localhost:5000")  # Or remote server
mlflow.set_experiment("project_name")

def train_with_mlflow(config: Dict[str, Any]) -> None:
    """Train model with MLflow tracking."""
    with mlflow.start_run(run_name=f"experiment_{config['model_type']}"):
        # Log parameters
        mlflow.log_params(config)
        
        # Log dataset info
        mlflow.log_param("dataset_size", len(train_data))
        mlflow.log_param("features", train_data.shape[1])
        
        # Train model
        model = create_model(config)
        history = train_model(model, train_data, val_data, config)
        
        # Log metrics
        for epoch, metrics in enumerate(history):
            mlflow.log_metrics({
                "train_loss": metrics["train_loss"],
                "val_loss": metrics["val_loss"],
                "train_accuracy": metrics["train_accuracy"],
                "val_accuracy": metrics["val_accuracy"]
            }, step=epoch)
        
        # Log final metrics
        final_metrics = evaluate_model(model, test_data)
        mlflow.log_metrics(final_metrics)
        
        # Log model
        mlflow.pytorch.log_model(
            model, 
            "model",
            registered_model_name=f"{config['model_type']}_v{config['version']}"
        )
        
        # Log artifacts
        mlflow.log_artifact("configs/model_config.yaml")
        mlflow.log_artifact("plots/training_curves.png")
```

### Option 2: Weights & Biases
```python
import wandb

def train_with_wandb(config: Dict[str, Any]) -> None:
    """Train model with W&B tracking."""
    # Initialize run
    run = wandb.init(
        project="project_name",
        config=config,
        name=f"experiment_{config['model_type']}"
    )
    
    # Train model
    model = create_model(config)
    
    for epoch in range(config['epochs']):
        train_loss, train_acc = train_epoch(model, train_loader)
        val_loss, val_acc = validate_epoch(model, val_loader)
        
        # Log metrics
        wandb.log({
            "epoch": epoch,
            "train_loss": train_loss,
            "train_accuracy": train_acc,
            "val_loss": val_loss,
            "val_accuracy": val_acc
        })
    
    # Log final model
    wandb.save("model.pt")
    
    # Finish run
    run.finish()
```

## Model Training Best Practices

### Training Configuration
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
import yaml

@dataclass
class TrainingConfig:
    """Training configuration class."""
    model_type: str
    learning_rate: float
    batch_size: int
    epochs: int
    optimizer: str = "adam"
    scheduler: Optional[str] = None
    early_stopping_patience: int = 10
    seed: int = 42
    device: str = "auto"
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'TrainingConfig':
        """Load configuration from YAML file."""
        with open(config_path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {k: v for k, v in self.__dict__.items()}
```

### Reproducible Training
```python
import random
import numpy as np
import torch

def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

class ModelTrainer:
    """Handles model training with best practices."""
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        set_seed(config.seed)
        self.device = self._get_device()
        
    def _get_device(self) -> torch.device:
        """Get appropriate device for training."""
        if self.config.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.config.device)
    
    def train(self, model: torch.nn.Module, 
              train_loader: torch.utils.data.DataLoader,
              val_loader: torch.utils.data.DataLoader) -> Dict[str, List[float]]:
        """Train model with validation and early stopping."""
        model = model.to(self.device)
        optimizer = self._create_optimizer(model)
        scheduler = self._create_scheduler(optimizer)
        criterion = self._create_criterion()
        
        history = {"train_loss": [], "val_loss": [], "train_acc": [], "val_acc": []}
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(self.config.epochs):
            # Training phase
            train_loss, train_acc = self._train_epoch(
                model, train_loader, optimizer, criterion
            )
            
            # Validation phase
            val_loss, val_acc = self._validate_epoch(
                model, val_loader, criterion
            )
            
            # Update history
            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)
            history["train_acc"].append(train_acc)
            history["val_acc"].append(val_acc)
            
            # Learning rate scheduling
            if scheduler:
                scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self._save_checkpoint(model, optimizer, epoch, val_loss)
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stopping_patience:
                    print(f"Early stopping at epoch {epoch}")
                    break
            
            print(f"Epoch {epoch}: train_loss={train_loss:.4f}, "
                  f"val_loss={val_loss:.4f}, val_acc={val_acc:.4f}")
        
        return history
```

## Evaluation Metrics Standards

### Classification Metrics
```python
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns

def evaluate_classification(y_true: np.ndarray, 
                          y_pred: np.ndarray, 
                          y_prob: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Comprehensive classification evaluation."""
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, average='weighted'),
        "recall": recall_score(y_true, y_pred, average='weighted'),
        "f1_score": f1_score(y_true, y_pred, average='weighted')
    }
    
    # Add AUC if probabilities provided
    if y_prob is not None:
        if len(np.unique(y_true)) == 2:  # Binary classification
            metrics["auc_roc"] = roc_auc_score(y_true, y_prob[:, 1])
        else:  # Multi-class
            metrics["auc_roc"] = roc_auc_score(y_true, y_prob, multi_class='ovr')
    
    return metrics

def plot_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, 
                         class_names: List[str]) -> None:
    """Plot confusion matrix."""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png', dpi=300, bbox_inches='tight')
```

### Regression Metrics
```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Comprehensive regression evaluation."""
    return {
        "mse": mean_squared_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "mae": mean_absolute_error(y_true, y_pred),
        "r2_score": r2_score(y_true, y_pred),
        "mape": np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    }
```

### Model Comparison
```python
def compare_models(models: Dict[str, Any], 
                  test_data: Tuple[np.ndarray, np.ndarray]) -> pd.DataFrame:
    """Compare multiple models on test data."""
    X_test, y_test = test_data
    results = []
    
    for model_name, model in models.items():
        y_pred = model.predict(X_test)
        
        if hasattr(model, 'predict_proba'):
            y_prob = model.predict_proba(X_test)
            metrics = evaluate_classification(y_test, y_pred, y_prob)
        else:
            metrics = evaluate_regression(y_test, y_pred)
        
        metrics['model'] = model_name
        results.append(metrics)
    
    return pd.DataFrame(results).set_index('model')
```

## Model Deployment Checklist

### Pre-deployment Validation
```python
def validate_model_for_deployment(model: Any, 
                                test_data: Tuple[np.ndarray, np.ndarray],
                                requirements: Dict[str, Any]) -> Dict[str, bool]:
    """Validate model meets deployment requirements."""
    X_test, y_test = test_data
    validation_results = {}
    
    # Performance requirements
    y_pred = model.predict(X_test)
    if hasattr(model, 'predict_proba'):
        metrics = evaluate_classification(y_test, y_pred, model.predict_proba(X_test))
        validation_results['meets_accuracy_threshold'] = (
            metrics['accuracy'] >= requirements.get('min_accuracy', 0.8)
        )
    else:
        metrics = evaluate_regression(y_test, y_pred)
        validation_results['meets_rmse_threshold'] = (
            metrics['rmse'] <= requirements.get('max_rmse', 1.0)
        )
    
    # Latency requirements
    import time
    start_time = time.time()
    _ = model.predict(X_test[:100])  # Sample batch
    inference_time = (time.time() - start_time) / 100
    validation_results['meets_latency_requirement'] = (
        inference_time <= requirements.get('max_latency_ms', 100) / 1000
    )
    
    # Memory requirements
    import psutil
    process = psutil.Process()
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
    validation_results['meets_memory_requirement'] = (
        memory_usage <= requirements.get('max_memory_mb', 1000)
    )
    
    return validation_results
```

### Model Packaging
```python
import joblib
import json
from datetime import datetime

def package_model(model: Any, 
                 metadata: Dict[str, Any],
                 model_path: str) -> str:
    """Package model with metadata for deployment."""
    # Create model package directory
    package_dir = f"{model_path}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(package_dir, exist_ok=True)
    
    # Save model
    model_file = f"{package_dir}/model.pkl"
    joblib.dump(model, model_file)
    
    # Save metadata
    package_metadata = {
        "model_type": type(model).__name__,
        "created_at": datetime.now().isoformat(),
        "version": metadata.get("version", "1.0.0"),
        "metrics": metadata.get("metrics", {}),
        "training_config": metadata.get("config", {}),
        "dependencies": metadata.get("dependencies", []),
        "input_schema": metadata.get("input_schema", {}),
        "output_schema": metadata.get("output_schema", {})
    }
    
    with open(f"{package_dir}/metadata.json", 'w') as f:
        json.dump(package_metadata, f, indent=2)
    
    # Create requirements.txt
    with open(f"{package_dir}/requirements.txt", 'w') as f:
        for dep in package_metadata["dependencies"]:
            f.write(f"{dep}\n")
    
    return package_dir
```

## Reproducibility Requirements

### Environment Management
```python
# requirements.txt with pinned versions
"""
torch==2.0.1
transformers==4.21.0
scikit-learn==1.3.0
pandas==2.0.3
numpy==1.24.3
"""

# Environment export
def export_environment() -> Dict[str, str]:
    """Export current environment for reproducibility."""
    import pkg_resources
    
    installed_packages = {
        pkg.project_name: pkg.version 
        for pkg in pkg_resources.working_set
    }
    
    return installed_packages
```

### Experiment Configuration
```yaml
# configs/experiment_config.yaml
experiment:
  name: "bert_classification_v1"
  description: "BERT fine-tuning for text classification"
  
model:
  type: "bert"
  pretrained_model: "bert-base-uncased"
  num_classes: 2
  dropout: 0.1

training:
  learning_rate: 2e-5
  batch_size: 16
  epochs: 3
  warmup_steps: 500
  weight_decay: 0.01
  seed: 42

data:
  train_path: "data/processed/train.csv"
  val_path: "data/processed/val.csv"
  test_path: "data/processed/test.csv"
  text_column: "text"
  label_column: "label"
  max_length: 512

evaluation:
  metrics: ["accuracy", "f1", "precision", "recall"]
  save_predictions: true
  save_confusion_matrix: true
```

### Reproducibility Checklist
- [ ] **Random seeds set** for all random operations
- [ ] **Dependencies pinned** to specific versions
- [ ] **Data versions tracked** and documented
- [ ] **Model architecture** saved with hyperparameters
- [ ] **Training procedure** documented step-by-step
- [ ] **Environment exported** (requirements.txt, conda env)
- [ ] **Hardware specifications** documented
- [ ] **Evaluation protocol** clearly defined

## Model Monitoring

### Performance Monitoring
```python
def monitor_model_performance(model: Any,
                            new_data: Tuple[np.ndarray, np.ndarray],
                            baseline_metrics: Dict[str, float],
                            threshold: float = 0.05) -> Dict[str, Any]:
    """Monitor model performance against baseline."""
    X_new, y_new = new_data
    y_pred = model.predict(X_new)
    
    # Calculate current metrics
    if hasattr(model, 'predict_proba'):
        current_metrics = evaluate_classification(y_new, y_pred, model.predict_proba(X_new))
    else:
        current_metrics = evaluate_regression(y_new, y_pred)
    
    # Compare with baseline
    alerts = {}
    for metric, baseline_value in baseline_metrics.items():
        if metric in current_metrics:
            current_value = current_metrics[metric]
            degradation = (baseline_value - current_value) / baseline_value
            
            alerts[f"{metric}_degradation"] = degradation
            alerts[f"{metric}_alert"] = degradation > threshold
    
    return {
        "current_metrics": current_metrics,
        "baseline_metrics": baseline_metrics,
        "alerts": alerts,
        "timestamp": datetime.now().isoformat()
    }
```

### Data Drift Monitoring
```python
from scipy.stats import ks_2samp

def monitor_data_drift(reference_data: np.ndarray,
                      current_data: np.ndarray,
                      feature_names: List[str],
                      threshold: float = 0.05) -> Dict[str, Any]:
    """Monitor for data drift in input features."""
    drift_results = {}
    
    for i, feature_name in enumerate(feature_names):
        if i < reference_data.shape[1] and i < current_data.shape[1]:
            # Kolmogorov-Smirnov test
            statistic, p_value = ks_2samp(
                reference_data[:, i], 
                current_data[:, i]
            )
            
            drift_results[feature_name] = {
                "ks_statistic": statistic,
                "p_value": p_value,
                "drift_detected": p_value < threshold
            }
    
    return drift_results
```

## Best Practices Summary

### Experiment Management
1. **Track everything**: Parameters, metrics, artifacts, environment
2. **Use consistent naming**: Experiments, runs, models
3. **Document hypotheses**: What you're testing and why
4. **Compare systematically**: Use same evaluation protocol
5. **Archive results**: Keep successful experiments accessible

### Model Development
1. **Start simple**: Baseline models first
2. **Iterate quickly**: Small, testable changes
3. **Validate rigorously**: Multiple evaluation metrics
4. **Test edge cases**: Boundary conditions and failure modes
5. **Monitor continuously**: Performance and data drift

### Deployment Preparation
1. **Package completely**: Model, metadata, dependencies
2. **Test thoroughly**: Performance, latency, memory
3. **Document clearly**: API, inputs, outputs, limitations
4. **Plan monitoring**: Metrics, alerts, rollback procedures
5. **Version everything**: Models, data, code, configurations