# Practical 4: Parallel and Distributed Computing Fundamentals

This practical session covers parallel and distributed computing concepts in Python, including functional programming, multiprocessing, and performance optimization.

## Prerequisites

- Docker and Docker Compose installed
- Basic knowledge of Python programming

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Build and start the container:**

   ```bash
   docker-compose up --build
   ```

2. **Access Jupyter Lab:**

   Open your browser and navigate to:
   ```
   http://localhost:8888
   ```

3. **Open the notebook:**

   Navigate to `/app/notebooks/practical4.ipynb` in Jupyter Lab.

4. **Stop the container:**

   ```bash
   docker-compose down
   ```

### Option 2: Using Docker directly

1. **Build the image:**

   ```bash
   docker build -t practical4 .
   ```

2. **Run the container with volume mounts:**

   ```bash
   docker run -it --rm \
     -p 8888:8888 \
     -v $(pwd)/practical4.ipynb:/app/notebooks/practical4.ipynb \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/output:/app/output \
     practical4
   ```

3. **Access Jupyter Lab:**

   Open `http://localhost:8888` in your browser.

## Directory Structure

```
practical4/
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── practical4.ipynb    # The main notebook
├── data/               # Data files (mounted volume)
└── output/             # Output files (mounted volume)
```

## Exercises Overview

| Exercise | Topic | Difficulty |
|----------|-------|------------|
| 1 | Functional Programming (filter, map, reduce) | ★ |
| 2 | Lambda Expressions and Higher-Order Functions | ★ |
| 3 | Generators and Iterators | ★★ |
| 4 | Introduction to Multiprocessing | ★★ |
| 5 | Process Communication (Queues and Pipes) | ★★ |
| 6 | concurrent.futures and Async Patterns | ★★★ |
| 7 | Performance Benchmarking and Optimization | ★★★ |

## Installed Packages

The Docker image includes:

- **Jupyter**: JupyterLab for interactive notebook environment
- **NumPy/Pandas**: Numerical computing and data manipulation
- **Matplotlib**: Data visualization
- **Dask**: Parallel computing with task scheduling
- **Joblib**: Lightweight pipelining and parallel computing
- **memory-profiler**: Memory usage profiling
- **psutil**: System and process utilities

## Working with Volumes

### Data Volume

The `data/` directory is mounted to `/app/data` in the container. Place your input files here:

```bash
# Create data directory
mkdir -p data

# Copy data files
cp your_data.csv data/
```

### Output Volume

The `output/` directory is mounted to `/app/output` in the container. Results will be saved here:

```python
# In your notebook
import pandas as pd

results = pd.DataFrame(...)
results.to_csv('/app/output/results.csv')
```

## Troubleshooting

### Port Already in Use

If port 8888 is already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8889:8888"  # Use port 8889 instead
```

### Permission Issues on Linux

If you encounter permission issues with mounted volumes:

```bash
# Set proper permissions
chmod -R 777 data output
```

Or run with your user ID:

```bash
docker run -it --rm \
  -p 8888:8888 \
  -u $(id -u):$(id -g) \
  -v $(pwd)/practical4.ipynb:/app/notebooks/practical4.ipynb \
  -v $(pwd)/data:/app/data \
  practical4
```

### Memory Issues with Multiprocessing

The notebook includes exercises with multiprocessing. If you encounter memory issues:

1. **Increase Docker memory limit:**

   In Docker Desktop, go to Settings > Resources > Memory and increase the limit.

2. **Or add memory limits to docker-compose.yml:**

   ```yaml
   services:
     jupyter:
       ...
       deploy:
         resources:
           limits:
             memory: 4G
   ```

### Kernel Crashes

If the Jupyter kernel crashes during multiprocessing exercises:

1. Restart the kernel from the Jupyter interface
2. Run cells one at a time instead of "Run All"
3. Reduce the number of processes in Pool() calls

## CPU Configuration for Multiprocessing

By default, Docker containers have access to all host CPUs. To limit CPU access:

```yaml
# In docker-compose.yml
services:
  jupyter:
    ...
    deploy:
      resources:
        limits:
          cpus: '4'  # Limit to 4 CPUs
```

## Running Tests

To verify the environment is set up correctly:

```bash
# Enter the container
docker-compose exec jupyter bash

# Run a quick test
python -c "
import multiprocessing
import numpy as np
import pandas as pd
print(f'CPUs available: {multiprocessing.cpu_count()}')
print(f'NumPy version: {np.__version__}')
print(f'Pandas version: {pd.__version__}')
print('All dependencies installed correctly!')
"
```

## Additional Resources

- [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html)
- [concurrent.futures documentation](https://docs.python.org/3/library/concurrent.futures.html)
- [Dask documentation](https://docs.dask.org/)
- [Jupyter documentation](https://jupyter.org/documentation)

## License

This practical is part of the TDM (Traitement de Données Massives) course.
