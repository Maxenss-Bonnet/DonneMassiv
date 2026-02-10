# Project: Image Recommendation System

## Overview

In this project, you will build an **Image Recommendation System** that suggests images to users based on their preferences. This project applies all the skills you learned in the practical sessions: data parsing, visualization, clustering, classification, and machine learning.

**Duration**: 3 practical sessions
**Team Size**: 2-3 students
**Deliverables**:
1. A Jupyter notebook (`Name1_Name2_[Name3].ipynb`)
2. A 4-page summary report (PDF)

---

## Learning Objectives

By completing this project, you will:
- Automate data collection from web sources
- Extract and process image metadata
- Apply clustering algorithms to analyze image features
- Build user preference profiles
- Implement a recommendation algorithm
- Visualize data insights effectively
- Write comprehensive tests for your system

---

## Project Architecture

The system consists of 7 interconnected tasks:

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMAGE RECOMMENDATION SYSTEM                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 1. Data      │───▶│ 2. Labeling  │───▶│ 3. Data      │       │
│  │ Collection   │    │ & Annotation │    │ Analysis     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│        │                    │                   │                │
│        ▼                    ▼                   ▼                │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              JSON Files (Metadata Storage)            │       │
│  └──────────────────────────────────────────────────────┘       │
│        │                    │                   │                │
│        ▼                    ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ 4. Data      │    │ 5. Recommend-│    │ 6. Tests     │       │
│  │ Visualization│    │ ation System │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                             │                                    │
│                             ▼                                    │
│                    ┌──────────────┐                              │
│                    │ 7. Summary   │                              │
│                    │    Report    │                              │
│                    └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

![Architecture](../../images/Project-Architecture.png "Architecture")

---

## Project Part 1

---

### Task 1: Data Collection

#### Goal
Collect at least **100 open-licensed images** with their metadata.

#### What You Need to Do

1. **Create a folder structure**:
   ```
   project/
   ├── images/           # Downloaded images
   ├── data/             # JSON metadata files
   └── project.ipynb     # Your notebook
   ```

2. **Find image sources** (choose one or more):
   - [Wikimedia Commons](https://commons.wikimedia.org/) - Use SPARQL queries (like in Practical 1)
   - [Unsplash API](https://unsplash.com/developers) - Free API for high-quality images
   - [Pexels API](https://www.pexels.com/api/) - Free stock photos
   - [Flickr API](https://www.flickr.com/services/api/) - Creative Commons images

3. **Download images programmatically** using the techniques from Practical 1, Exercise 6

4. **Extract and save metadata** for each image:
   - Image filename
   - Image dimensions (width, height)
   - File format (.jpg, .png, etc.)
   - File size (in KB)
   - Source URL
   - License information
   - EXIF data (if available): camera model, date taken, etc.

#### Expected Output
- `images/` folder with 100+ images
- `data/images_metadata.json` containing metadata for all images

#### Hints
- Use `PIL` to get image dimensions
- Use `os.path.getsize()` to get file size
- Use EXIF extraction (see Practical 2, Exercise 2)
- Store metadata as a list of dictionaries in JSON format

---

### Task 2: Labeling and Annotation

#### Goal
Add descriptive labels and computed features to each image.

#### What You Need to Do

1. **Extract color information** using KMeans clustering (Practical 2, Exercise 3):
   - Find the 3-5 predominant colors in each image
   - Store colors as RGB values and/or color names

2. **Determine image orientation**:
   - Landscape (width > height)
   - Portrait (height > width)
   - Square (width ≈ height)

3. **Add category tags** (choose an approach):
   - **Manual**: Create a simple interface to tag images
   - **Automated**: Use image source categories/tags
   - **Hybrid**: Start with source tags, allow user refinement

4. **Classify image size**:
   - Thumbnail: < 500px
   - Medium: 500-1500px
   - Large: > 1500px

#### Expected Output
- `data/images_labels.json` with enriched metadata:
```json
{
  "image_001.jpg": {
    "predominant_colors": [[255, 128, 0], [0, 100, 200], [50, 50, 50]],
    "color_names": ["orange", "blue", "gray"],
    "orientation": "landscape",
    "size_category": "medium",
    "tags": ["nature", "sunset", "beach"]
  }
}
```

#### Hints
- Reuse your KMeans color extraction code from Practical 2
- Consider using a color name mapping (RGB → color name)
- Store all annotations in a structured JSON file

---

### Task 3: Data Analysis

#### Goal
Build user preference profiles based on their image selections.

#### What You Need to Do

1. **Simulate users** (create at least 5 users):
   - Each user "favorites" 10-20 images
   - Users should have different preferences (one likes nature, another likes architecture, etc.)

2. **Build user profiles** by analyzing their favorite images:
   ```python
   user_profile = {
       "user_id": "user_001",
       "favorite_colors": ["blue", "green"],      # Most common colors
       "favorite_orientation": "landscape",        # Most common orientation
       "favorite_size": "medium",                  # Most common size
       "favorite_tags": ["nature", "water"],       # Most common tags
       "favorite_images": ["img_01.jpg", ...]      # List of favorited images
   }
   ```

3. **Analyze patterns** across users:
   - Which colors are most popular overall?
   - Which tags appear most frequently?
   - Are there clusters of users with similar preferences?

#### Expected Output
- `data/users.json` with user profiles
- Analysis results showing user preference patterns

#### Hints
- Use pandas for data analysis (groupby, value_counts)
- Use Counter from collections to find most common items
- Consider using clustering to group similar users

---

### Task 4: Data Visualization

#### Goal
Create visualizations that reveal insights about your image collection and user preferences.

#### Required Visualizations

1. **Image Collection Statistics**:
   - Bar chart: Number of images per orientation
   - Bar chart: Number of images per size category
   - Pie chart: Distribution of image formats

2. **Color Analysis**:
   - Display predominant colors as color palettes
   - Histogram of color frequencies across all images

3. **User Preferences**:
   - Bar chart: Favorite colors per user
   - Comparison chart: User preferences side-by-side

4. **Tag Analysis**:
   - Bar chart: Most common tags
   - Word cloud (optional): Tag frequency visualization

#### Expected Output
- At least 6 different visualizations in your notebook
- All plots should have titles, labels, and legends

#### Hints
- Use matplotlib for all visualizations (Practical 2, Exercise 1)
- Save important plots using `plt.savefig()`
- Use subplots to group related visualizations

---

### Task 5: Recommendation System

#### Goal
Implement a system that recommends images to users based on their preferences.

#### Choose Your Approach

You must implement **at least one** of these approaches:

##### Option A: Content-Based Filtering (Using Classification)
Recommend images similar to what the user has liked before.

```python
# Train a classifier on user's favorites
# Features: color, orientation, size, tags
# Label: Favorite / Not Favorite
# Predict which unseen images the user would like
```

**Use**: Decision Tree, Random Forest, or SVM (Practical 3, Exercises 2-3)

##### Option B: Clustering-Based Recommendation
Group similar images together and recommend from the same cluster.

```python
# Cluster all images based on features
# Find which cluster the user's favorites belong to
# Recommend other images from the same cluster
```

**Use**: KMeans (Practical 2, Exercises 3-5)

##### Option C: Hybrid Approach
Combine both methods for better recommendations.

#### Implementation Requirements

1. **Input**: User ID
2. **Output**: List of 5-10 recommended images (not already favorited)
3. **Explanation**: Brief reason why each image is recommended

#### Expected Output
```python
def recommend_images(user_id, n_recommendations=5):
    """
    Recommend images for a user.

    Args:
        user_id: The user to recommend for
        n_recommendations: Number of images to recommend

    Returns:
        List of (image_filename, reason) tuples
    """
    # Your implementation
    pass
```

#### Hints
- Start with the examples in `examples/recommendation.ipynb`
- Use LabelEncoder to convert categorical features to numbers
- Test your recommendations manually - do they make sense?

---

### Task 6: Tests

#### Goal
Verify that your system works correctly.

#### Required Tests

1. **Data Validation Tests**:
   - All images exist in the images folder
   - All images have metadata
   - Metadata values are valid (no negative dimensions, etc.)

2. **Function Tests**:
   - Color extraction returns valid RGB values
   - User profile generation works correctly
   - Recommendation function returns the expected number of results

3. **Recommendation Quality Tests**:
   - Recommended images are not already in user's favorites
   - Recommendations match user preferences (e.g., if user likes blue images, recommendations should include blue images)

#### Expected Output
```python
def test_data_integrity():
    """Test that all data is valid"""
    # Your tests
    assert len(images) >= 100, "Need at least 100 images"
    assert all_images_have_metadata(), "Missing metadata"

def test_recommendation_system():
    """Test that recommendations work"""
    recommendations = recommend_images("user_001", 5)
    assert len(recommendations) == 5, "Should return 5 recommendations"
    # More tests...
```

#### Hints
- Use `assert` statements for simple tests
- Print clear pass/fail messages
- Test edge cases (empty user profile, new user, etc.)

---

### Task 7: Summary Report

#### Goal
Write a 4-page report summarizing your project.

#### Required Sections

1. **Introduction** (0.5 page)
   - Project goal
   - Your approach in brief

2. **Data Collection** (0.5 page)
   - Image sources and licenses
   - Number of images collected
   - Metadata stored

3. **Methodology** (1.5 pages)
   - Labeling approach (how you extracted features)
   - User profile construction
   - Recommendation algorithm chosen and why
   - Include architecture diagram

4. **Results** (1 page)
   - Key visualizations (2-3 figures)
   - Recommendation accuracy/quality
   - Interesting findings

5. **Limitations and Future Work** (0.25 page)
   - What didn't work well?
   - How could it be improved?

6. **Conclusion** (0.25 page)
   - Summary of achievements
   - Self-evaluation

#### Format
- 4 pages maximum
- PDF format
- No code in the report (only results and explanations)
- Include references/bibliography

---

### Evaluation (Part 1)

| Task | Points | Key Criteria |
|------|--------|--------------|
| Data Collection | 15% | Automation, 100+ images, complete metadata |
| Labeling & Annotation | 15% | Color extraction, proper categorization |
| Data Analysis | 15% | User profiles, preference analysis |
| Data Visualization | 15% | 6+ visualizations, proper formatting |
| Recommendation System | 20% | Working algorithm, reasonable recommendations |
| Tests | 10% | Comprehensive tests, all pass |
| Summary Report | 10% | Clear, complete, well-structured |

---

### Submission (Part 1)

#### Files to Submit
```
Name1_Name2_[Name3].zip
├── Name1_Name2_[Name3].ipynb    # Your notebook
├── data/
│   ├── images_metadata.json
│   ├── images_labels.json
│   └── users.json
└── summary_report.pdf
```

#### Important Notes
- **DO NOT** submit the images folder (too large)
- Ensure your notebook runs without errors
- Include comments explaining your code
- Rename files with your team member names

---

### Getting Started

1. Start with the template notebook: `en/Project/project.ipynb`
2. Review the examples in `examples/recommendation.ipynb`
3. Reuse code from your practical sessions
4. Work incrementally - complete each task before moving to the next

**Note**: You can check [supplementary examples](../../examples) of notebooks.

---

## Project Part 2

The goal of Part 2 is to transform your Part 1 project into a **distributed, containerized application** using Docker (Practical 6) and PySpark (Practical 5). You will decompose your monolithic notebook into independent, scalable services that communicate through shared data volumes.

### Overview

In Part 1, your entire pipeline (data collection, labeling, analysis, visualization, recommendation) runs inside a single Jupyter notebook. In Part 2, you will:

1. **Identify the independent tasks** from your Part 1 pipeline
2. **Replace sequential loops with PySpark operations** (map-reduce, lambda expressions)
3. **Package each task as a Docker container** with its own Dockerfile
4. **Use Docker volumes** to share data (JSON, CSV, images) between containers
5. **Orchestrate everything** with `docker-compose`

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        docker-compose.yml                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│  │  Container 1:     │   │  Container 2:     │   │  Container 3:  │   │
│  │  Data Acquisition │──▶│  Data Analysis    │──▶│ Recommendation │   │
│  │                   │   │  & Labeling       │   │                │   │
│  │  - Download imgs  │   │  - Color extract  │   │ - User profile │   │
│  │  - Extract EXIF   │   │  - Clustering     │   │ - Recommend    │   │
│  │  - Save metadata  │   │  - User profiles  │   │ - Visualize    │   │
│  └────────┬──────────┘   └────────┬──────────┘   └───────┬────────┘   │
│           │                       │                       │            │
│           ▼                       ▼                       ▼            │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Shared Docker Volume                       │     │
│  │  /shared_data/                                                │     │
│  │  ├── images/               # Downloaded images                │     │
│  │  ├── images_metadata.json  # From Container 1                 │     │
│  │  ├── images_labels.json    # From Container 2                 │     │
│  │  ├── users.json            # From Container 2                 │     │
│  │  └── recommendations.json  # From Container 3                 │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Step 1: Identify Independent Tasks

Review your Part 1 notebook and separate it into at least **three independent tasks**. A suggested decomposition:

| Container | Part 1 Tasks Covered | Input | Output |
|-----------|---------------------|-------|--------|
| **Data Acquisition** | Task 1 (Data Collection) | Image source URLs | `images/`, `images_metadata.json` |
| **Data Analysis & Labeling** | Task 2 (Labeling), Task 3 (Analysis), Task 4 (Visualization) | `images/`, `images_metadata.json` | `images_labels.json`, `users.json`, visualization PNGs |
| **Recommendation** | Task 5 (Recommendation), Task 6 (Tests) | `images_labels.json`, `users.json` | `recommendations.json`, test results |

You may split these further into more containers (e.g., separate containers for labeling, analysis, and visualization).

### Step 2: Replace Loops with PySpark Operations

For each container, identify the **sequential loops** from your Part 1 code and rewrite them using PySpark's distributed operations:

#### Example: Color Extraction (from Task 2)

**Part 1 (sequential loop):**
```python
# Processing images one by one in a loop
results = []
for image_file in image_files:
    img = load_image(image_file)
    colors = extract_colors(img)
    results.append({"file": image_file, "colors": colors})
```

**Part 2 (PySpark):**
```python
from pyspark import SparkContext

sc = SparkContext("local[*]", "ColorExtraction")

# Distribute image file list across workers
images_rdd = sc.parallelize(image_files)

# Map: apply color extraction to each image in parallel
colors_rdd = images_rdd.map(lambda f: (f, extract_colors(load_image(f))))

# Collect results
results = colors_rdd.collect()
```

#### Example: User Profile Building (from Task 3)

**Part 1 (sequential loop):**
```python
# Building profiles one user at a time
profiles = []
for user in users:
    fav_colors = []
    for img in user["favorites"]:
        fav_colors.extend(labels[img]["color_names"])
    most_common = Counter(fav_colors).most_common(3)
    profiles.append({"user": user["id"], "colors": most_common})
```

**Part 2 (PySpark):**
```python
# Distribute user processing with RDDs
users_rdd = sc.parallelize(users)

# Map each user to their profile using lambda
profiles_rdd = users_rdd.map(lambda u: build_user_profile(u, labels))

# Use reduceByKey for aggregating tag counts across all users
all_tags_rdd = users_rdd.flatMap(lambda u: get_user_tags(u, labels)) \
                        .map(lambda tag: (tag, 1)) \
                        .reduceByKey(lambda a, b: a + b)

top_tags = all_tags_rdd.sortBy(lambda x: x[1], ascending=False).take(10)
```

#### Example: Recommendation Scoring (from Task 5)

**Part 1 (sequential loop):**
```python
# Scoring images for a user sequentially
scores = []
for img in all_images:
    score = compute_similarity(user_profile, image_features[img])
    scores.append((img, score))
scores.sort(key=lambda x: x[1], reverse=True)
```

**Part 2 (PySpark):**
```python
# Distribute scoring across workers
images_rdd = sc.parallelize(all_images)

# Map: compute similarity score in parallel
scores_rdd = images_rdd.map(lambda img: (img, compute_similarity(user_profile, image_features[img])))

# Sort and take top recommendations
recommendations = scores_rdd.sortBy(lambda x: x[1], ascending=False).take(10)
```

### Step 3: Create Docker Containers

Each container needs its own:
- **Dockerfile** with the required dependencies (Python, PySpark, libraries)
- **Python script(s)** implementing the task with PySpark operations
- **requirements.txt** listing the Python dependencies

Refer to Practical 6 examples for container structure:
- `SharedVolume/` example for volume-based communication between containers
- `AppDB/` example for multi-container orchestration

#### Example Dockerfile for the Data Analysis container:

```dockerfile
FROM python:3.10-slim

# Install Java (required for PySpark)
RUN apt-get update && apt-get install -y openjdk-17-jdk-headless && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyze.py .
CMD ["python", "analyze.py"]
```

#### Example requirements.txt:
```
pyspark==3.5.3
numpy==1.26.4
Pillow==10.4.0
```

### Step 4: Use Docker Volumes for Data Sharing

Use a shared Docker volume so that containers can read and write data files (JSON, CSV, images). Each container reads its input from the shared volume and writes its output to the shared volume.

#### Example docker-compose.yml:

```yaml
version: "3.8"

services:
  acquisition:
    build: ./acquisition
    volumes:
      - shared_data:/shared_data
    environment:
      - OUTPUT_DIR=/shared_data

  analysis:
    build: ./analysis
    depends_on:
      acquisition:
        condition: service_completed_successfully
    volumes:
      - shared_data:/shared_data
    environment:
      - INPUT_DIR=/shared_data
      - OUTPUT_DIR=/shared_data

  recommendation:
    build: ./recommendation
    depends_on:
      analysis:
        condition: service_completed_successfully
    volumes:
      - shared_data:/shared_data
    environment:
      - INPUT_DIR=/shared_data
      - OUTPUT_DIR=/shared_data

volumes:
  shared_data:
```

### Step 5: Run and Verify

```bash
# Build and run all containers in sequence
docker compose up --build

# Check the shared volume for outputs
docker compose run --rm recommendation ls /shared_data/
```

### Evaluation (Part 2)

| Criteria | Points | Details |
|----------|--------|---------|
| Task decomposition | 25% | Clear separation into 3+ independent containers, each with a well-defined input/output |
| Docker volumes | 25% | Correct use of shared volumes for passing JSON, CSV, and image files between containers |
| Map-reduce & lambda expressions | 25% | Sequential loops from Part 1 replaced with PySpark `map`, `flatMap`, `filter`, `reduceByKey`, and lambda expressions |
| PySpark usage | 25% | Correct use of SparkContext, RDD operations, and distributed processing in at least 2 containers |

**Note**: You can check [supplementary examples](../../examples) of Docker containers and the examples in Practical 5 and Practical 6.
