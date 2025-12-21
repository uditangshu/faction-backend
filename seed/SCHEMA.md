# Seed Data Schema Documentation

This document describes the JSON schema for seeding questions and PYQ (Previous Year Questions) into the database.

## Overview

The seed script accepts a JSON array where each object represents a question with its hierarchy (Class → Subject → Chapter → Topic) and optional PYQ information.

## Schema Structure

```json
[
  {
    "class_level": "string | int",
    "subject_type": "string",
    "chapter_name": "string",
    "topic_name": "string",
    "exam_types": ["string"],
    "question": { ... },
    "pyq": { ... } | null
  }
]
```

## Field Descriptions

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `class_level` | string \| int | Yes | Class level: `"Ninth"`, `"Tenth"`, `"Eleventh"`, `"Twelth"` or `9`, `10`, `11`, `12` |
| `subject_type` | string | Yes | Subject type: `"PHYSICS"`, `"CHEMISTRY"`, `"MATHS"`, `"BIOLOGY"` |
| `chapter_name` | string | Yes | Name of the chapter (e.g., "Mechanics", "Organic Chemistry") |
| `topic_name` | string | Yes | Name of the topic (e.g., "Newton's Laws", "Alkanes") |
| `exam_types` | array[string] | No | List of exam types this subject applies to. Default: `["JEE_MAINS"]` |
| `question` | object | Yes | Question data object (see Question Object below) |
| `pyq` | object \| null | No | PYQ data object (see PYQ Object below). Set to `null` if not a PYQ |

### Question Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Question type: `"integer"`, `"mcq"`, `"scq"`, `"match_the_column"` or `"match"` |
| `difficulty` | string \| int | Yes | Difficulty level: `"easy"`/`1`, `"medium"`/`2`, `"hard"`/`3` |
| `exam_type` | array[string] | Yes | Exam types: `"JEE_ADVANCED"`, `"JEE_MAINS"`, `"NEET"`, `"OLYMPIAD"`, `"CBSE"` |
| `question_text` | string | Yes | The question text/content |
| `marks` | int | No | Marks for the question. Default: `4` |
| `solution_text` | string | No | Solution/explanation text. Default: `""` |
| `question_image` | string \| null | No | URL or path to question image. Default: `null` |
| `integer_answer` | int \| null | No | **For integer type**: The integer answer |
| `mcq_options` | array[string] \| null | No | **For MCQ type**: List of option strings |
| `mcq_correct_option` | array[int] \| null | No | **For MCQ type**: List of correct option indices (0-based) |
| `scq_options` | array[string] \| null | No | **For SCQ type**: List of option strings |
| `scq_correct_options` | int \| null | No | **For SCQ type**: Index of correct option (0-based) |

### PYQ Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `year` | int | No | Year of the exam. Default: `2024` |
| `exam_detail` | array[string] | No | Additional exam details (e.g., `["JEE_MAINS", "Paper 1", "Shift 1"]`). Default: `[]` |

## Question Type Details

### 1. Integer Type (`"integer"`)
- Requires: `integer_answer`
- Example:
```json
{
  "type": "integer",
  "integer_answer": 42
}
```

### 2. MCQ Type (`"mcq"`)
- Requires: `mcq_options`, `mcq_correct_option`
- `mcq_correct_option` is an array of indices (0-based) for multiple correct answers
- Example:
```json
{
  "type": "mcq",
  "mcq_options": ["Option A", "Option B", "Option C", "Option D"],
  "mcq_correct_option": [1, 2]  // Options B and C are correct
}
```

### 3. SCQ Type (`"scq"`)
- Requires: `scq_options`, `scq_correct_options`
- `scq_correct_options` is a single integer index (0-based)
- Example:
```json
{
  "type": "scq",
  "scq_options": ["Option A", "Option B", "Option C", "Option D"],
  "scq_correct_options": 2  // Option C is correct
}
```

### 4. Match the Column Type (`"match_the_column"` or `"match"`)
- Uses `mcq_options` and `mcq_correct_option` format
- Typically has options like "A-1, B-2, C-3, D-4"
- Example:
```json
{
  "type": "match_the_column",
  "mcq_options": [
    "A-1, B-2, C-3, D-4",
    "A-2, B-1, C-4, D-3",
    "A-3, B-4, C-1, D-2"
  ],
  "mcq_correct_option": [0]
}
```

## Enum Values Reference

### Class Levels
- `"Ninth"` or `9`
- `"Tenth"` or `10`
- `"Eleventh"` or `11`
- `"Twelth"` or `12`

### Subject Types
- `"PHYSICS"`
- `"CHEMISTRY"`
- `"MATHS"`
- `"BIOLOGY"`

### Question Types
- `"integer"` - Integer answer type
- `"mcq"` - Multiple Choice Question (single or multiple correct)
- `"scq"` - Single Choice Question
- `"match_the_column"` or `"match"` - Match the column type

### Difficulty Levels
- `"easy"` or `1` - Easy difficulty
- `"medium"` or `2` - Medium difficulty
- `"hard"` or `3` - Hard difficulty

### Exam Types
- `"JEE_ADVANCED"` - JEE Advanced
- `"JEE_MAINS"` - JEE Mains
- `"NEET"` - NEET
- `"OLYMPIAD"` - Olympiad
- `"CBSE"` - CBSE

## Complete Example

See `example_data.json` for complete examples of all question types with PYQ data.

## Usage

```bash
# Using default example file
python seed/seed.py

# Using custom data file
python seed/seed.py --data path/to/your/data.json
```

## Notes

1. The script automatically creates Class, Subject, Chapter, and Topic entries if they don't exist
2. If a Subject already exists, its exam_types will be updated if different
3. Questions are committed in batches of 50 for better performance
4. PYQ entries are optional - set `"pyq": null` if the question is not a previous year question
5. All string comparisons are case-insensitive for enums
6. The script will skip duplicate questions if they have the same text, but it's recommended to ensure uniqueness in your data

