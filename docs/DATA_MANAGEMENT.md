# Data Management

This document outlines data storage, versioning, privacy, and security practices for AI/ML projects.

## Data Storage Structure

### Directory Organization
```
data/
├── raw/                    # Original, immutable data
│   ├── source1/           # Data from first source
│   ├── source2/           # Data from second source
│   └── metadata/          # Data documentation
├── processed/             # Cleaned and transformed data
│   ├── train/            # Training datasets
│   ├── validation/       # Validation datasets
│   ├── test/             # Test datasets
│   └── features/         # Feature engineering outputs
├── external/             # Third-party datasets
│   ├── public/           # Public datasets
│   └── licensed/         # Licensed datasets
└── interim/              # Intermediate processing results
    ├── experiments/      # Experiment-specific data
    └── temp/            # Temporary files
```

### File Naming Conventions
```
# Format: <dataset>_<version>_<date>_<description>.<ext>
customer_data_v1.2_20231201_cleaned.parquet
model_predictions_v2.0_20231215_test_set.csv
features_v1.0_20231210_engineered.pkl

# Experiment data
exp_001_bert_training_data_20231201.jsonl
exp_002_roberta_validation_results_20231205.csv
```

## Data Versioning

### **[CUSTOMIZE]** Choose your data versioning tool:

### Option 1: DVC (Data Version Control)
```bash
# Initialize DVC
dvc init

# Add data to version control
dvc add data/raw/dataset.csv
git add data/raw/dataset.csv.dvc .gitignore
git commit -m "Add dataset v1.0"

# Push data to remote storage
dvc push

# Retrieve specific version
dvc checkout dataset.csv.dvc
```

### Option 2: Git LFS (for smaller datasets)
```bash
# Track large files
git lfs track "*.csv"
git lfs track "*.parquet"
git add .gitattributes

# Add and commit data
git add data/raw/dataset.csv
git commit -m "Add dataset v1.0"
```

### Option 3: Manual Versioning
```python
# Version tracking in metadata
import json
from datetime import datetime

def create_data_version(data_path: str, description: str) -> str:
    """Create version metadata for dataset."""
    version_info = {
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "description": description,
        "file_path": data_path,
        "file_size": os.path.getsize(data_path),
        "checksum": calculate_checksum(data_path)
    }
    
    metadata_path = f"{data_path}.metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(version_info, f, indent=2)
    
    return metadata_path
```

## Data Quality and Validation

### Data Validation Pipeline
```python
import pandas as pd
from typing import Dict, List, Any
import great_expectations as ge

def validate_dataset(df: pd.DataFrame, schema: Dict[str, Any]) -> Dict[str, bool]:
    """Validate dataset against schema."""
    results = {}
    
    # Check required columns
    required_cols = schema.get('required_columns', [])
    results['has_required_columns'] = all(col in df.columns for col in required_cols)
    
    # Check data types
    for col, expected_type in schema.get('column_types', {}).items():
        if col in df.columns:
            results[f'{col}_correct_type'] = str(df[col].dtype) == expected_type
    
    # Check value ranges
    for col, range_info in schema.get('value_ranges', {}).items():
        if col in df.columns:
            min_val, max_val = range_info['min'], range_info['max']
            results[f'{col}_in_range'] = df[col].between(min_val, max_val).all()
    
    # Check for nulls
    for col in schema.get('no_nulls', []):
        if col in df.columns:
            results[f'{col}_no_nulls'] = not df[col].isnull().any()
    
    return results

# Example schema
DATASET_SCHEMA = {
    'required_columns': ['id', 'text', 'label'],
    'column_types': {
        'id': 'int64',
        'text': 'object',
        'label': 'int64'
    },
    'value_ranges': {
        'label': {'min': 0, 'max': 1}
    },
    'no_nulls': ['id', 'text', 'label']
}
```

### Data Quality Checks
```python
def run_data_quality_checks(df: pd.DataFrame) -> Dict[str, Any]:
    """Run comprehensive data quality checks."""
    report = {
        'total_rows': len(df),
        'total_columns': len(df.columns),
        'missing_values': df.isnull().sum().to_dict(),
        'duplicate_rows': df.duplicated().sum(),
        'memory_usage': df.memory_usage(deep=True).sum(),
        'column_stats': {}
    }
    
    # Column-specific statistics
    for col in df.columns:
        if df[col].dtype in ['int64', 'float64']:
            report['column_stats'][col] = {
                'mean': df[col].mean(),
                'std': df[col].std(),
                'min': df[col].min(),
                'max': df[col].max(),
                'unique_values': df[col].nunique()
            }
        else:
            report['column_stats'][col] = {
                'unique_values': df[col].nunique(),
                'most_common': df[col].value_counts().head(5).to_dict()
            }
    
    return report
```

## Privacy and Security

### Data Classification
```python
from enum import Enum

class DataClassification(Enum):
    PUBLIC = "public"           # No restrictions
    INTERNAL = "internal"       # Company internal only
    CONFIDENTIAL = "confidential"  # Restricted access
    RESTRICTED = "restricted"   # Highly sensitive

# Data classification metadata
DATA_CATALOG = {
    "customer_data": {
        "classification": DataClassification.CONFIDENTIAL,
        "contains_pii": True,
        "retention_period": "7_years",
        "access_level": "data_team_only"
    },
    "public_dataset": {
        "classification": DataClassification.PUBLIC,
        "contains_pii": False,
        "retention_period": "indefinite",
        "access_level": "all_team_members"
    }
}
```

### PII Handling
```python
import hashlib
import re
from typing import Optional

def anonymize_pii(text: str) -> str:
    """Remove or anonymize PII from text."""
    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                  '[EMAIL]', text)
    
    # Phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
    
    # Social Security Numbers
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', text)
    
    return text

def hash_identifier(identifier: str, salt: str = "default_salt") -> str:
    """Hash identifiers for pseudonymization."""
    return hashlib.sha256(f"{identifier}{salt}".encode()).hexdigest()[:16]
```

### Data Access Control
```python
import os
from functools import wraps

def require_data_access(classification: DataClassification):
    """Decorator to enforce data access controls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_level = os.getenv('USER_ACCESS_LEVEL', 'public')
            
            access_levels = {
                DataClassification.PUBLIC: ['public', 'internal', 'confidential', 'restricted'],
                DataClassification.INTERNAL: ['internal', 'confidential', 'restricted'],
                DataClassification.CONFIDENTIAL: ['confidential', 'restricted'],
                DataClassification.RESTRICTED: ['restricted']
            }
            
            if user_level not in access_levels[classification]:
                raise PermissionError(f"Insufficient access level for {classification.value} data")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

@require_data_access(DataClassification.CONFIDENTIAL)
def load_customer_data():
    """Load confidential customer data."""
    pass
```

## Dataset Documentation

### Dataset Documentation Template
```python
# Create dataset_info.json for each dataset
DATASET_INFO_TEMPLATE = {
    "name": "dataset_name",
    "version": "1.0.0",
    "description": "Detailed description of the dataset",
    "source": {
        "origin": "internal/external/public",
        "url": "source_url_if_applicable",
        "contact": "data_owner@company.com"
    },
    "collection": {
        "method": "how_data_was_collected",
        "date_range": "2023-01-01_to_2023-12-31",
        "frequency": "daily/weekly/monthly/one-time"
    },
    "schema": {
        "columns": [
            {
                "name": "column_name",
                "type": "data_type",
                "description": "column_description",
                "nullable": True,
                "unique": False
            }
        ]
    },
    "statistics": {
        "total_rows": 10000,
        "total_size_mb": 50.2,
        "missing_values_percent": 2.1
    },
    "quality": {
        "completeness": 0.98,
        "accuracy": 0.95,
        "consistency": 0.97
    },
    "privacy": {
        "classification": "confidential",
        "contains_pii": True,
        "anonymization_applied": True
    },
    "usage": {
        "purpose": "model_training",
        "restrictions": "internal_use_only",
        "expiration_date": "2024-12-31"
    }
}
```

### Automated Documentation
```python
def generate_dataset_documentation(df: pd.DataFrame, dataset_name: str) -> Dict:
    """Generate automatic dataset documentation."""
    doc = {
        "name": dataset_name,
        "generated_at": datetime.now().isoformat(),
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": [],
        "summary_statistics": {}
    }
    
    for col in df.columns:
        col_info = {
            "name": col,
            "type": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "null_percentage": float(df[col].isnull().mean() * 100),
            "unique_count": int(df[col].nunique())
        }
        
        if df[col].dtype in ['int64', 'float64']:
            col_info.update({
                "mean": float(df[col].mean()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            })
        
        doc["columns"].append(col_info)
    
    return doc
```

## Data Pipeline Best Practices

### ETL Pipeline Structure
```python
from abc import ABC, abstractmethod
import logging

class DataProcessor(ABC):
    """Abstract base class for data processing steps."""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"data_processor.{name}")
    
    @abstractmethod
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process the data."""
        pass
    
    def validate_input(self, data: pd.DataFrame) -> None:
        """Validate input data."""
        if data.empty:
            raise ValueError("Input data is empty")
    
    def validate_output(self, data: pd.DataFrame) -> None:
        """Validate output data."""
        if data.empty:
            self.logger.warning("Output data is empty")

class DataPipeline:
    """Data processing pipeline."""
    
    def __init__(self, processors: List[DataProcessor]):
        self.processors = processors
        self.logger = logging.getLogger("data_pipeline")
    
    def run(self, data: pd.DataFrame) -> pd.DataFrame:
        """Run the complete pipeline."""
        self.logger.info("Starting data pipeline")
        
        for processor in self.processors:
            self.logger.info(f"Running processor: {processor.name}")
            processor.validate_input(data)
            data = processor.process(data)
            processor.validate_output(data)
        
        self.logger.info("Data pipeline completed")
        return data
```

### Data Backup and Recovery
```python
import shutil
from pathlib import Path

def backup_data(source_path: str, backup_path: str) -> str:
    """Create backup of data directory."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{backup_path}/backup_{timestamp}"
    
    shutil.copytree(source_path, backup_dir)
    
    # Create backup manifest
    manifest = {
        "backup_time": timestamp,
        "source_path": source_path,
        "backup_path": backup_dir,
        "files_count": len(list(Path(backup_dir).rglob("*")))
    }
    
    with open(f"{backup_dir}/manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return backup_dir
```

## Monitoring and Alerting

### Data Drift Detection
```python
from scipy import stats
import numpy as np

def detect_data_drift(reference_data: pd.DataFrame, 
                     current_data: pd.DataFrame,
                     threshold: float = 0.05) -> Dict[str, bool]:
    """Detect data drift using statistical tests."""
    drift_results = {}
    
    for col in reference_data.columns:
        if col in current_data.columns:
            if reference_data[col].dtype in ['int64', 'float64']:
                # Use KS test for numerical data
                statistic, p_value = stats.ks_2samp(
                    reference_data[col].dropna(),
                    current_data[col].dropna()
                )
                drift_results[col] = p_value < threshold
            else:
                # Use chi-square test for categorical data
                ref_counts = reference_data[col].value_counts()
                curr_counts = current_data[col].value_counts()
                
                # Align categories
                all_categories = set(ref_counts.index) | set(curr_counts.index)
                ref_aligned = [ref_counts.get(cat, 0) for cat in all_categories]
                curr_aligned = [curr_counts.get(cat, 0) for cat in all_categories]
                
                if sum(ref_aligned) > 0 and sum(curr_aligned) > 0:
                    statistic, p_value = stats.chisquare(curr_aligned, ref_aligned)
                    drift_results[col] = p_value < threshold
    
    return drift_results
```

## Compliance and Governance

### **[CUSTOMIZE]** Update with your compliance requirements:

### GDPR Compliance (if applicable)
```python
def handle_data_deletion_request(user_id: str, datasets: List[str]) -> Dict[str, bool]:
    """Handle GDPR data deletion requests."""
    deletion_results = {}
    
    for dataset in datasets:
        try:
            # Remove user data from dataset
            df = pd.read_parquet(f"data/{dataset}.parquet")
            df_filtered = df[df['user_id'] != user_id]
            df_filtered.to_parquet(f"data/{dataset}.parquet", index=False)
            
            # Log deletion
            log_data_deletion(user_id, dataset)
            deletion_results[dataset] = True
            
        except Exception as e:
            logging.error(f"Failed to delete data for user {user_id} from {dataset}: {e}")
            deletion_results[dataset] = False
    
    return deletion_results
```

### Audit Trail
```python
def log_data_access(user: str, dataset: str, operation: str) -> None:
    """Log data access for audit purposes."""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "user": user,
        "dataset": dataset,
        "operation": operation,
        "ip_address": get_client_ip(),
        "session_id": get_session_id()
    }
    
    # Write to audit log
    with open("logs/data_access.log", "a") as f:
        f.write(json.dumps(audit_entry) + "\n")
```