# Bulk User Import Template

## Template Structure

Create an Excel file (.xlsx) with the following columns:

### For Students:
| Column Name | Required | Example | Notes |
|------------|----------|---------|-------|
| username | Yes | john.doe | Unique login username |
| email | Yes | john@example.com | Must be unique |
| password | Yes | Student@123 | Will be hashed automatically |
| first_name | Yes | John | Student's first name |
| last_name | Yes | Doe | Student's last name |
| role | Yes | student | Must be "student" |
| full_name | Yes | John Doe | Full display name |
| roll_number | No | STU-2024-001 | Student roll number |
| admission_id | No | ADM-001 | Admission ID |
| grade | No | AS Level | Grade/class name |
| division | No | A | Section/division |

### For Teachers:
| Column Name | Required | Example | Notes |
|------------|----------|---------|-------|
| username | Yes | jane.smith | Unique login username |
| email | Yes | jane@example.com | Must be unique |
| password | Yes | Teacher@123 | Will be hashed automatically |
| first_name | Yes | Jane | Teacher's first name |
| last_name | Yes | Smith | Teacher's last name |
| role | Yes | teacher | Must be "teacher" |
| subject | No | Physics | Subject taught |

## Sample Data

### Students Sheet:
```
username,email,password,first_name,last_name,role,full_name,roll_number,admission_id,grade,division
alice.johnson,alice@school.com,Pass@1234,Alice,Johnson,student,Alice Johnson,2024001,ADM001,AS Level,A
bob.williams,bob@school.com,Pass@1234,Bob,Williams,student,Bob Williams,2024002,ADM002,AS Level,A
charlie.brown,charlie@school.com,Pass@1234,Charlie,Brown,student,Charlie Brown,2024003,ADM003,A Level,B
```

### Teachers Sheet:
```
username,email,password,first_name,last_name,role,subject
john.physics,john.p@school.com,Teach@123,John,Peterson,teacher,Physics
mary.chem,mary.c@school.com,Teach@123,Mary,Chen,teacher,Chemistry
```

## Creating the Template

### Method 1: Create in Excel
1. Open Microsoft Excel or Google Sheets
2. Add column headers in Row 1
3. Fill in sample data in rows 2+
4. Save as .xlsx file

### Method 2: Use CSV
1. Create a CSV file with the structure above
2. Open in Excel and save as .xlsx

## Usage Instructions

1. Download/Create the template with correct column headers
2. Fill in user details (one user per row)
3. Save the file as .xlsx format
4. Go to Teacher Dashboard → Users → Bulk Import
5. Upload the Excel file
6. Review the preview
7. Click "Import Users" to process

## Important Notes

- **Passwords**: Will be hashed before storing (secure)
- **Usernames**: Must be unique across the school
- **Emails**: Must be unique and valid
- **Roles**: Exactly "student" or "teacher" (lowercase)
- **Grades**: Will be created if they don't exist
- **Empty cells**: Optional fields can be left blank
- **Duplicate check**: System will skip users with existing usernames/emails

## Error Handling

If import fails:
- Check column names match exactly
- Ensure required fields are filled
- Verify email format is valid
- Check for duplicate usernames/emails
- Review error messages in upload page
