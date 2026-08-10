---
name: ML Experiment
about: Document a machine learning experiment
title: '[EXPERIMENT] '
labels: experiment, ml
assignees: ''
---

## Experiment Overview
**Experiment Name**: [Descriptive name for the experiment]

**Hypothesis**: [What you expect to achieve or test]

**Objective**: [Clear statement of what you're trying to accomplish]

## Background
**Problem Statement**: [What problem are you trying to solve?]

**Previous Work**: [Related experiments or baseline results]

**Motivation**: [Why is this experiment important?]

## Experimental Setup
### Dataset
- **Dataset Name**: [Name of dataset used]
- **Dataset Size**: [Number of samples, features, etc.]
- **Data Split**: [Train/Val/Test split ratios]
- **Data Preprocessing**: [Steps taken to prepare data]

### Model Architecture
- **Model Type**: [e.g., BERT, ResNet, Custom CNN]
- **Model Size**: [Parameters, layers, etc.]
- **Pre-trained**: [Yes/No, which checkpoint]
- **Modifications**: [Any changes to standard architecture]

### Training Configuration
- **Learning Rate**: [e.g., 2e-5]
- **Batch Size**: [e.g., 16]
- **Epochs**: [e.g., 10]
- **Optimizer**: [e.g., AdamW]
- **Scheduler**: [e.g., Linear warmup]
- **Hardware**: [e.g., 1x RTX 3080, 4x V100]
- **Training Time**: [Expected or actual duration]

### Hyperparameters
```yaml
# Paste your configuration here
model:
  type: "bert-base-uncased"
  dropout: 0.1
  
training:
  learning_rate: 2e-5
  batch_size: 16
  epochs: 3
```

## Evaluation Metrics
**Primary Metrics**: [Main metrics for evaluation]
- [ ] Accuracy
- [ ] F1 Score
- [ ] Precision/Recall
- [ ] AUC-ROC
- [ ] BLEU Score
- [ ] Other: [Specify]

**Secondary Metrics**: [Additional metrics to track]
- [ ] Training Time
- [ ] Inference Latency
- [ ] Memory Usage
- [ ] Model Size

## Expected Results
**Baseline Performance**: [Current best results]

**Expected Improvement**: [What improvement you expect]

**Success Criteria**: [How you'll determine if experiment succeeded]

## Actual Results
### Performance Metrics
| Metric | Baseline | Experiment | Improvement |
|--------|----------|------------|-------------|
| Accuracy | 0.85 | 0.87 | +2.4% |
| F1 Score | 0.82 | 0.84 | +2.4% |
| Training Time | 2h | 2.5h | +25% |

### Key Findings
- [Finding 1]
- [Finding 2]
- [Finding 3]

### Unexpected Results
- [Any surprising or unexpected outcomes]

## Analysis
### What Worked Well
- [Successful aspects of the experiment]

### What Didn't Work
- [Unsuccessful aspects or failures]

### Lessons Learned
- [Key insights from the experiment]

## Visualizations
[Add plots, charts, or other visualizations]
- Training curves
- Confusion matrices
- Feature importance plots
- Error analysis

## Reproducibility
### Code Location
- **Branch**: [Git branch with experiment code]
- **Commit**: [Specific commit hash]
- **Scripts**: [Main training/evaluation scripts]

### Environment
- **Python Version**: [e.g., 3.9.7]
- **Key Dependencies**: 
  ```
  torch==2.0.1
  transformers==4.21.0
  ```
- **Random Seed**: [Seed used for reproducibility]

### Data Version
- **Data Commit**: [DVC commit or version]
- **Data Location**: [Path to data used]

## Next Steps
### Follow-up Experiments
- [ ] [Next experiment idea 1]
- [ ] [Next experiment idea 2]
- [ ] [Next experiment idea 3]

### Improvements to Try
- [ ] [Improvement idea 1]
- [ ] [Improvement idea 2]
- [ ] [Improvement idea 3]

### Questions for Further Investigation
- [Question 1]
- [Question 2]
- [Question 3]

## Resources Used
- **Compute Time**: [GPU hours used]
- **Storage**: [Data storage requirements]
- **Cost**: [If applicable]

## Experiment Status
- [ ] Planning
- [ ] In Progress
- [ ] Completed
- [ ] Failed
- [ ] Cancelled

## Related Work
- Related to experiment #[issue_number]
- Builds on #[issue_number]
- Compares with #[issue_number]

## Additional Notes
[Any other relevant information, observations, or context]