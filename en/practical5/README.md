# Practical 5: Apache Spark for Massive Data Processing

This practical session introduces Apache Spark, a powerful distributed computing framework for large-scale data processing. You will learn RDDs, DataFrames, Spark SQL, and performance optimization techniques.

## Prerequisites

- Docker and Docker Compose installed
- Basic knowledge of Python programming
- Completion of Practical 4 (Parallel and Distributed Computing)

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Build and start the container:**

   ```bash
   docker-compose up --build
   ```
   
   Note: Avoid using `--no-cache` unless you really need a clean rebuild. Spark is large and Docker will reuse the cached download layer on subsequent builds.

2. **Access Jupyter Lab:**

   Open your browser and navigate to:
   ```
   http://localhost:8888
   ```

3. **Access Spark UI (when running Spark jobs):**

   ```
   http://localhost:4040
   ```

4. **Open the notebook:**

   Navigate to `/app/notebooks/practical5.ipynb` in Jupyter Lab.

5. **Stop the container:**

   ```bash
   docker-compose down
   ```

### Option 2: Using Docker directly

1. **Build the image:**

   ```bash
   docker build -t practical5-spark .
   ```

2. **Run the container with volume mounts:**

   ```bash
   docker run -it --rm \
     -p 8888:8888 \
     -p 4040:4040 \
     --shm-size=2g \
     -v $(pwd)/practical5.ipynb:/app/notebooks/practical5.ipynb \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/output:/app/output \
     practical5-spark
   ```

3. **Access Jupyter Lab:**

   Open `http://localhost:8888` in your browser.

## Directory Structure

```
practical5/
├── Dockerfile           # Docker image definition with Java and Spark
├── docker-compose.yml   # Docker Compose configuration
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── practical5.ipynb    # The main notebook
├── data/               # Data files (mounted volume)
└── output/             # Output files (mounted volume)
```

## Exercises Overview

| Exercise | Topic | Difficulty |
|----------|-------|------------|
| 1 | Spark Architecture and RDD Basics | ★ |
| 2 | RDD Transformations and Actions | ★ |
| 3 | DataFrames and Schema Management | ★★ |
| 4 | Spark SQL and Complex Queries | ★★ |
| 5 | Joins, Window Functions, and Aggregations | ★★ |
| 6 | Partitioning, Caching, and Optimization | ★★★ |
| 7 | Processing Large-Scale Datasets | ★★★ |

## Installed Components

The Docker image includes:

### Java Runtime
- **OpenJDK 17**: Required for Apache Spark

### Python Packages
- **PySpark**: Apache Spark Python API
- **Jupyter**: JupyterLab for interactive notebook environment
- **NumPy/Pandas**: Numerical computing and data manipulation
- **Matplotlib**: Data visualization
- **PyArrow**: Efficient Spark/Pandas conversion
- **psutil**: System and process utilities

## Working with Volumes

### Data Volume

The `data/` directory is mounted to `/app/data` in the container. Additionally, the shared data directory is mounted to `/app/shared_data`.

```bash
# Create data directory
mkdir -p data

# Copy data files
cp your_data.csv data/
```

### Output Volume

The `output/` directory is mounted to `/app/output` in the container. Results will be saved here:

```python
# In your notebook - save Parquet files
df.write.parquet('/app/output/results.parquet')

# Save CSV files
df.write.csv('/app/output/results.csv')
```

## Spark Configuration

### Memory Settings

The default configuration allocates 2GB for both driver and executor memory. Modify in `docker-compose.yml`:

```yaml
environment:
  - SPARK_DRIVER_MEMORY=4g
  - SPARK_EXECUTOR_MEMORY=4g
```

### Shared Memory

Spark requires sufficient shared memory. The default is 2GB. Increase if needed:

```yaml
shm_size: '4gb'
```

### Accessing Spark UI

When running Spark jobs, the Spark UI is available at:
```
http://localhost:4040
```

This provides information about:
- Active and completed jobs
- Stages and tasks
- Storage (cached RDDs/DataFrames)
- Environment configuration
- Executors

## Troubleshooting

### Port Already in Use

If port 8888 or 4040 is already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "8889:8888"  # Use port 8889 for Jupyter
  - "4041:4040"  # Use port 4041 for Spark UI
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
  -p 4040:4040 \
  -u $(id -u):$(id -g) \
  -v $(pwd)/practical5.ipynb:/app/notebooks/practical5.ipynb \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  practical5-spark
```

### Memory Issues

Spark can be memory-intensive. If you encounter out-of-memory errors:

1. **Increase Docker memory limit:**

   In Docker Desktop, go to Settings > Resources > Memory and increase the limit to at least 4GB.

2. **Increase container memory:**

   ```yaml
   services:
     jupyter-spark:
       ...
       deploy:
         resources:
           limits:
             memory: 6G
   ```

3. **Reduce data size for exercises:**

   When working with large datasets, start with smaller samples:

   ```python
   # Sample 10% of data
   sampled_df = large_df.sample(fraction=0.1)
   ```

### Java Not Found

If you see Java-related errors, verify Java is installed:

```bash
docker-compose exec jupyter-spark java -version
```

### Spark Session Issues

If SparkContext is already running:

```python
# Stop existing context
sc.stop()

# Or get existing session
spark = SparkSession.builder.getOrCreate()
```

### Kernel Crashes

If the Jupyter kernel crashes during Spark operations:

1. Restart the kernel from the Jupyter interface
2. Reduce the amount of data being processed
3. Increase memory allocation
4. Use `persist()` with DISK storage level for large datasets

## Running Tests

To verify the environment is set up correctly:

```bash
# Enter the container
docker-compose exec jupyter-spark bash

# Run a quick test
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('test').getOrCreate()
print(f'Spark Version: {spark.version}')
print(f'Java Home: $(echo \$JAVA_HOME)')
df = spark.range(10)
print(f'Test DataFrame count: {df.count()}')
spark.stop()
print('PySpark is working correctly!')
"
```

## Performance Tips

1. **Use DataFrames over RDDs** when possible for better optimization
2. **Cache intermediate results** that are used multiple times
3. **Use columnar formats** (Parquet/ORC) for large datasets
4. **Partition data** by frequently filtered columns
5. **Use broadcast joins** for small lookup tables
6. **Monitor with Spark UI** to identify bottlenecks

## Additional Resources

- [Apache Spark Documentation](https://spark.apache.org/docs/latest/)
- [PySpark API Reference](https://spark.apache.org/docs/latest/api/python/)
- [Spark SQL Guide](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [Spark Performance Tuning](https://spark.apache.org/docs/latest/tuning.html)

## License

This practical is part of the TDM (Traitement de Donnees Massives) course.
