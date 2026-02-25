# Answer Spaces Designer - PowerPoint-Style Interface

## 🎯 Overview

The new Answer Spaces Designer provides a **visual, PowerPoint-like interface** for configuring where and how students will answer questions during tests.

Instead of configuring abstract "parts", you now:
- **See the question image**
- **Draw answer placeholders** directly on it
- **Position them exactly** where answers should appear
- Students see these **same placeholders** during tests

---

## 🚀 How to Use

### Step 1: Access the Designer

Navigate to: `http://127.0.0.1:8000/questions/<question_id>/answer-spaces/`

### Step 2: Choose Answer Type

Click on one of the 5 preset types on the right sidebar:

1. **📝 Long Answer** - Multi-space for calculations, no lines
2. **📄 Long Answer (Lined)** - Multiple lines for definitions/descriptions
3. **✏️ Short Answer** - Single line input
4. **🔢 Half-Line** - Final answer box (for table cells)
5. **🎨 Canvas** - Drawing with lines, angles, shapes, colors

### Step 3: Draw Placeholder

After selecting a type:
1. **Click and drag** on the question image
2. A **dashed box** appears showing the answer space
3. Release to create the placeholder

### Step 4: Adjust Placeholder

**Move**: Click and drag the placeholder
**Resize**: Drag the corner handles (white circles)
**Delete**: Click the placeholder, then click "Delete" in the sidebar

### Step 5: Configure Answer Space

Click a placeholder to edit:
- **Label**: e.g., "Answer (a)", "Final answer", "Diagram"
- **Marks**: How many marks this space is worth
- **Model Answer**: The correct answer or grading criteria

### Step 6: Save Configuration

Click **"💾 Save Configuration"** when done.

---

## 📋 Answer Space Types

### 1. Long Answer (No Lines)
**Use for**: Calculations, working space, scratch work

**Rendered as**: Large textarea with no line guides

**Best for**:
- Mathematical calculations
- Physics derivations
- Chemistry equations

**Example**: "Show your working for calculating the velocity"

---

### 2. Long Answer (Lined)
**Use for**: Definitions, descriptions, explanations

**Rendered as**: Textarea with horizontal line guides

**Best for**:
- Essay-style answers
- Definitions
- Explanations
- Descriptive responses

**Example**: "Explain the process of photosynthesis"

---

### 3. Short Answer
**Use for**: Brief responses, single words/numbers

**Rendered as**: Single-line input field

**Best for**:
- One-word answers
- Short phrases
- Numerical answers with units

**Example**: "State the formula for kinetic energy"

---

### 4. Half-Line
**Use for**: Final answers, table cells

**Rendered as**: Compact single-line box

**Best for**:
- Final numerical answers
- Answers inside table cells
- Multiple choice selections
- True/False responses

**Example**: Inside a table: "pH = ___"

---

### 5. Canvas
**Use for**: Diagrams, drawings, graphs

**Rendered as**: Drawing canvas with tools

**Tools available**:
- **Pen**: Free drawing
- **Line**: Straight lines
- **Shapes**: Circles, rectangles, triangles
- **Angles**: Angle markers
- **Colors**: Basic color palette
- **Eraser**: Remove mistakes

**Best for**:
- Ray diagrams
- Circuit diagrams
- Geometric constructions
- Graphs and plots
- Force diagrams

**Example**: "Draw the ray diagram for a convex lens"

---

## 💡 Best Practices

### Positioning

✅ **DO**: Place placeholders exactly where you want students to write
✅ **DO**: Leave enough space for handwritten/typed answers
✅ **DO**: Align placeholders neatly with question parts
❌ **DON'T**: Overlap placeholders
❌ **DON'T**: Make placeholders too small (hard to use)

### Sizing

- **Long Answer**: At least 300×200 pixels
- **Long Answer (Lined)**: At least 400×300 pixels
- **Short Answer**: At least 200×40 pixels
- **Half-Line**: At least 100×30 pixels
- **Canvas**: At least 400×400 pixels for diagrams

### Labeling

✅ **Clear labels**: "Answer (a)", "Calculation", "Diagram"
✅ **Match question parts**: If question has (a), (b), (c), label accordingly
✅ **Indicate purpose**: "Show working", "Final answer only"

### Model Answers

✅ **Specific**: Write the exact expected answer
✅ **Detailed**: Include key points for grading
✅ **Grading criteria**: Note what earns marks

**Example**:
```
Model Answer: "Photosynthesis is the process where plants
convert light energy into chemical energy. Key points:
- Occurs in chloroplasts (1 mark)
- Uses CO2 + H2O (1 mark)
- Produces glucose + O2 (1 mark)
- Requires sunlight (1 mark)"
```

---

## 🎓 Example Workflows

### Example 1: Multi-Part Physics Question

**Question**: "A ball is thrown upward..."
- (a) Calculate initial velocity [3 marks]
- (b) Find maximum height [2 marks]
- (c) Draw velocity-time graph [3 marks]

**Setup**:
1. Select **"Long Answer"** → Draw placeholder under part (a)
   - Label: "Answer (a) - Show working"
   - Marks: 3
   - Model Answer: "v = u + at, v = 0, a = -9.8, solve for u..."

2. Select **"Half-Line"** → Draw small box for part (b) final answer
   - Label: "Final height"
   - Marks: 2
   - Model Answer: "h = 20.4 m"

3. Select **"Canvas"** → Draw large placeholder for graph
   - Label: "Velocity-Time Graph"
   - Marks: 3
   - Model Answer: "Linear graph, negative slope, intercepts at t=0 and t=4.08s"

---

### Example 2: Chemistry Definition Question

**Question**: "Define oxidation and give an example"

**Setup**:
1. Select **"Long Answer (Lined)"** → Draw placeholder
   - Label: "Definition and Example"
   - Marks: 4
   - Model Answer: "Oxidation is loss of electrons (1m). Example: 2Mg + O2 → 2MgO, Mg loses electrons (2m). Can also be gain of oxygen (1m)."

---

### Example 3: Biology Diagram

**Question**: "Label the parts of a plant cell"

**Setup**:
1. Select **"Canvas"** → Draw placeholder over the cell diagram
   - Label: "Label the diagram"
   - Marks: 6
   - Model Answer: "Cell wall, cell membrane, nucleus, chloroplast, vacuole, mitochondria (1 mark each)"

---

## 🔧 Technical Details

### Data Storage

Configuration is saved as JSON in the `parts_config` field:

```json
{
  "spaces": [
    {
      "id": "space_1",
      "type": "long_answer",
      "x": 50,
      "y": 100,
      "width": 400,
      "height": 200,
      "xPercent": 10.5,
      "yPercent": 15.2,
      "widthPercent": 45.3,
      "heightPercent": 25.6,
      "label": "Answer (a)",
      "marks": 3,
      "modelAnswer": "Expected answer here"
    }
  ],
  "imageWidth": 800,
  "imageHeight": 1200
}
```

### Responsive Rendering

- **Pixel values**: Used for designer interface
- **Percentage values**: Used for responsive student view
- **Scales automatically** to different screen sizes

### Student View Integration

During test-taking, placeholders are rendered:
1. Question image displayed at student's screen width
2. Answer spaces positioned using percentage values
3. Input type matches the configured type
4. Exactly matches the teacher's design

---

## 🎯 Comparison: Old vs New

### Old System ❌
- Configure abstract "parts" (a, b, c)
- No visual positioning
- Difficult to align with question
- Students see generic input boxes
- Hard to manage multi-part questions

### New System ✅
- Draw placeholders visually
- Exact positioning on question image
- WYSIWYG - What You See Is What You Get
- Students see same placeholders
- Intuitive drag-and-drop interface

---

## 🐛 Troubleshooting

### "Please select an answer type first"
**Solution**: Click one of the 5 type cards on the right before drawing

### Placeholder too small
**Solution**: Make sure to drag at least 50 pixels wide and 30 pixels high

### Can't move placeholder
**Solution**: Click directly on the placeholder (not the handles) and drag

### Lost my work
**Solution**: Changes are only saved when you click "Save Configuration"

### Placeholders not showing for students
**Solution**: Ensure you clicked "Save Configuration" after designing

---

## ⌨️ Keyboard Shortcuts

### Delete & Selection
- **Delete** - Delete the selected answer space
- **Esc** - Deselect all (clear selection)

### Movement (with space selected)
- **Arrow Keys (↑↓←→)** - Move selected space by 10 pixels
- **Ctrl + Arrow Keys** - Fine movement by 1 pixel (precise positioning)

### Quick Actions
- **Ctrl + D** - Duplicate the selected space
- **Ctrl + Z** - Undo last action (coming soon)

### Tips
✅ Select a space first (click on it) before using shortcuts
✅ Arrow keys won't work if typing in a text field
✅ Hold Ctrl for fine-grained 1px adjustments
✅ Use Delete key instead of clicking the delete button

---

## 🔮 Future Enhancements

- [ ] Copy/paste placeholders
- [ ] Duplicate placeholder across multiple questions
- [ ] Templates for common question types
- [ ] Auto-detect question parts from image (AI)
- [ ] Snap-to-grid alignment
- [ ] Keyboard shortcuts
- [ ] Undo/redo functionality

---

## 📚 Related Documentation

- **Question Import**: How to import questions with images
- **Test Creation**: Using questions with answer spaces in tests
- **Grading**: How answer spaces affect grading interface

---

**Last Updated**: 2026-02-01
**Version**: 2.0 - PowerPoint-Style Interface
