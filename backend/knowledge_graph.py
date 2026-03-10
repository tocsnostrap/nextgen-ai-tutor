import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Concept:
    id: str
    name: str
    subject: str
    grade_level: int
    difficulty: float
    prerequisites: List[str] = field(default_factory=list)
    description: str = ""
    learning_objectives: List[str] = field(default_factory=list)
    estimated_minutes: int = 15
    tags: List[str] = field(default_factory=list)


@dataclass
class Edge:
    source: str
    target: str
    relationship: str = "prerequisite"
    weight: float = 1.0


class KnowledgeGraph:
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.edges: List[Edge] = []
        self._build_curriculum()

    def _build_curriculum(self):
        self._build_math()
        self._build_science()
        self._build_reading()
        self._build_coding()
        self._build_edges()

    def _build_math(self):
        math_concepts = [
            Concept("math_counting", "Counting Numbers", "math", 0, 0.1, [], "Learn to count from 1 to 20", ["Count objects up to 20", "Recognize number symbols"], 10, ["numbers", "basics"]),
            Concept("math_number_recognition", "Number Recognition", "math", 0, 0.15, ["math_counting"], "Recognize and name numbers", ["Identify numbers 0-100", "Match quantities to numbers"], 10, ["numbers", "basics"]),
            Concept("math_addition_basic", "Basic Addition", "math", 1, 0.2, ["math_counting", "math_number_recognition"], "Add single-digit numbers", ["Add numbers up to 10", "Understand the plus sign"], 15, ["addition", "operations"]),
            Concept("math_subtraction_basic", "Basic Subtraction", "math", 1, 0.2, ["math_counting", "math_number_recognition"], "Subtract single-digit numbers", ["Subtract numbers up to 10", "Understand the minus sign"], 15, ["subtraction", "operations"]),
            Concept("math_addition_double", "Double-Digit Addition", "math", 2, 0.3, ["math_addition_basic"], "Add two-digit numbers", ["Add numbers up to 99", "Carry over tens"], 20, ["addition", "operations"]),
            Concept("math_subtraction_double", "Double-Digit Subtraction", "math", 2, 0.3, ["math_subtraction_basic"], "Subtract two-digit numbers", ["Subtract numbers up to 99", "Borrow from tens"], 20, ["subtraction", "operations"]),
            Concept("math_multiplication_intro", "Introduction to Multiplication", "math", 2, 0.3, ["math_addition_basic"], "Understand multiplication as repeated addition", ["Multiply by 2, 5, 10", "Understand times tables"], 20, ["multiplication", "operations"]),
            Concept("math_multiplication_tables", "Multiplication Tables", "math", 3, 0.4, ["math_multiplication_intro"], "Master multiplication tables 1-12", ["Recall times tables quickly", "Identify multiplication patterns"], 25, ["multiplication", "operations"]),
            Concept("math_division_intro", "Introduction to Division", "math", 3, 0.4, ["math_multiplication_intro"], "Understand division as sharing equally", ["Divide by single digits", "Understand remainders"], 20, ["division", "operations"]),
            Concept("math_fractions_intro", "Introduction to Fractions", "math", 3, 0.45, ["math_division_intro"], "Understand parts of a whole", ["Identify fractions", "Compare simple fractions"], 25, ["fractions", "numbers"]),
            Concept("math_fractions_operations", "Fraction Operations", "math", 4, 0.5, ["math_fractions_intro", "math_addition_double"], "Add and subtract fractions", ["Add fractions with same denominator", "Simplify fractions"], 30, ["fractions", "operations"]),
            Concept("math_decimals", "Decimals", "math", 4, 0.5, ["math_fractions_intro"], "Understand and use decimal numbers", ["Convert fractions to decimals", "Add and subtract decimals"], 25, ["decimals", "numbers"]),
            Concept("math_geometry_shapes", "Basic Shapes", "math", 1, 0.2, ["math_counting"], "Identify and describe basic shapes", ["Name 2D shapes", "Count sides and corners"], 15, ["geometry", "shapes"]),
            Concept("math_geometry_area", "Area and Perimeter", "math", 3, 0.4, ["math_geometry_shapes", "math_multiplication_intro"], "Calculate area and perimeter", ["Find area of rectangles", "Find perimeter of polygons"], 25, ["geometry", "measurement"]),
            Concept("math_geometry_volume", "Volume", "math", 5, 0.6, ["math_geometry_area", "math_multiplication_tables"], "Calculate volume of 3D shapes", ["Find volume of rectangular prisms", "Understand cubic units"], 30, ["geometry", "measurement"]),
            Concept("math_patterns", "Number Patterns", "math", 2, 0.25, ["math_addition_basic"], "Recognize and extend number patterns", ["Identify skip counting patterns", "Complete number sequences"], 15, ["patterns", "algebra"]),
            Concept("math_word_problems", "Word Problems", "math", 2, 0.35, ["math_addition_basic", "math_subtraction_basic"], "Solve simple word problems", ["Identify operations in word problems", "Write number sentences from stories"], 20, ["word problems", "reasoning"]),
            Concept("math_place_value", "Place Value", "math", 2, 0.3, ["math_number_recognition"], "Understand ones, tens, hundreds", ["Identify digit values", "Expand numbers by place value"], 20, ["numbers", "place value"]),
            Concept("math_measurement", "Measurement", "math", 2, 0.3, ["math_number_recognition", "math_addition_basic"], "Measure length, weight, and capacity", ["Use rulers and scales", "Compare measurements"], 20, ["measurement"]),
            Concept("math_time", "Telling Time", "math", 1, 0.25, ["math_number_recognition"], "Read clocks and understand time", ["Read analog and digital clocks", "Calculate elapsed time"], 15, ["time", "measurement"]),
            Concept("math_money", "Money", "math", 2, 0.3, ["math_addition_basic", "math_subtraction_basic"], "Count and use money", ["Identify coins and bills", "Make change"], 20, ["money", "real-world"]),
            Concept("math_data_graphs", "Data and Graphs", "math", 3, 0.35, ["math_counting", "math_addition_basic"], "Read and create graphs", ["Create bar graphs", "Interpret data tables"], 20, ["data", "statistics"]),
            Concept("math_order_operations", "Order of Operations", "math", 4, 0.5, ["math_addition_double", "math_multiplication_tables"], "Apply PEMDAS rules", ["Evaluate expressions with multiple operations", "Use parentheses correctly"], 25, ["operations", "algebra"]),
            Concept("math_pre_algebra", "Pre-Algebra Basics", "math", 5, 0.6, ["math_order_operations", "math_fractions_operations"], "Variables and simple equations", ["Solve for unknown variables", "Write algebraic expressions"], 30, ["algebra"]),
            Concept("math_ratios", "Ratios and Proportions", "math", 6, 0.65, ["math_fractions_operations", "math_multiplication_tables"], "Understand and use ratios", ["Write and simplify ratios", "Solve proportions"], 30, ["ratios", "algebra"]),
            Concept("math_percentages", "Percentages", "math", 6, 0.65, ["math_decimals", "math_fractions_operations"], "Understand and calculate percentages", ["Convert between fractions, decimals, and percentages", "Find percentage of a number"], 30, ["percentages", "numbers"]),
            Concept("math_integers", "Integers", "math", 6, 0.6, ["math_subtraction_double"], "Work with positive and negative numbers", ["Add and subtract integers", "Plot integers on number line"], 25, ["integers", "numbers"]),
            Concept("math_coordinate_plane", "Coordinate Plane", "math", 5, 0.55, ["math_integers", "math_geometry_shapes"], "Plot points on coordinate plane", ["Identify coordinates", "Plot ordered pairs"], 25, ["geometry", "algebra"]),
            Concept("math_probability", "Basic Probability", "math", 5, 0.55, ["math_fractions_intro", "math_data_graphs"], "Understand chance and likelihood", ["Calculate simple probabilities", "Describe events as likely/unlikely"], 25, ["probability", "statistics"]),
            Concept("math_exponents", "Exponents", "math", 6, 0.7, ["math_multiplication_tables", "math_pre_algebra"], "Understand powers and exponents", ["Evaluate expressions with exponents", "Understand square roots"], 30, ["exponents", "algebra"]),
        ]
        for c in math_concepts:
            self.concepts[c.id] = c

    def _build_science(self):
        science_concepts = [
            Concept("sci_living_things", "Living vs Non-Living", "science", 0, 0.1, [], "Identify living and non-living things", ["Classify objects as living or non-living", "Describe characteristics of living things"], 10, ["biology", "basics"]),
            Concept("sci_plants_basics", "Parts of Plants", "science", 1, 0.15, ["sci_living_things"], "Learn about plant parts and functions", ["Name parts of a plant", "Describe what plants need to grow"], 15, ["biology", "plants"]),
            Concept("sci_animals_basics", "Animal Groups", "science", 1, 0.15, ["sci_living_things"], "Learn about different animal groups", ["Classify animals into groups", "Describe animal habitats"], 15, ["biology", "animals"]),
            Concept("sci_habitats", "Habitats and Ecosystems", "science", 2, 0.25, ["sci_plants_basics", "sci_animals_basics"], "Understand where living things live", ["Describe different habitats", "Explain how animals adapt"], 20, ["biology", "ecology"]),
            Concept("sci_food_chains", "Food Chains", "science", 3, 0.35, ["sci_habitats"], "Understand food chains and webs", ["Identify producers and consumers", "Trace energy through food chains"], 20, ["biology", "ecology"]),
            Concept("sci_weather", "Weather", "science", 1, 0.15, [], "Observe and describe weather", ["Identify types of weather", "Use weather tools"], 15, ["earth science", "weather"]),
            Concept("sci_water_cycle", "Water Cycle", "science", 3, 0.35, ["sci_weather"], "Understand the water cycle", ["Describe evaporation and condensation", "Trace water through the cycle"], 20, ["earth science", "water"]),
            Concept("sci_earth_layers", "Earth's Layers", "science", 4, 0.45, [], "Learn about Earth's structure", ["Name and describe Earth's layers", "Understand plate tectonics basics"], 25, ["earth science", "geology"]),
            Concept("sci_rocks_minerals", "Rocks and Minerals", "science", 3, 0.3, ["sci_earth_layers"], "Identify types of rocks", ["Classify rocks as igneous, sedimentary, metamorphic", "Describe the rock cycle"], 20, ["earth science", "geology"]),
            Concept("sci_solar_system", "Solar System", "science", 3, 0.35, [], "Learn about planets and the sun", ["Name planets in order", "Describe Earth's place in the solar system"], 25, ["space", "astronomy"]),
            Concept("sci_moon_phases", "Moon Phases", "science", 4, 0.4, ["sci_solar_system"], "Understand moon phases", ["Identify moon phases", "Explain why the moon appears to change shape"], 20, ["space", "astronomy"]),
            Concept("sci_matter_states", "States of Matter", "science", 2, 0.25, [], "Understand solids, liquids, and gases", ["Classify matter by state", "Describe changes between states"], 15, ["physical science", "matter"]),
            Concept("sci_matter_properties", "Properties of Matter", "science", 3, 0.3, ["sci_matter_states"], "Measure and describe matter", ["Measure mass and volume", "Describe physical properties"], 20, ["physical science", "matter"]),
            Concept("sci_mixtures", "Mixtures and Solutions", "science", 4, 0.45, ["sci_matter_properties"], "Understand mixtures and solutions", ["Distinguish mixtures from solutions", "Describe methods of separation"], 25, ["physical science", "chemistry"]),
            Concept("sci_forces_motion", "Forces and Motion", "science", 3, 0.35, [], "Understand pushes, pulls, and movement", ["Describe how forces affect motion", "Identify types of forces"], 20, ["physical science", "physics"]),
            Concept("sci_simple_machines", "Simple Machines", "science", 4, 0.4, ["sci_forces_motion"], "Learn about levers, pulleys, and more", ["Identify simple machines", "Explain how they make work easier"], 25, ["physical science", "engineering"]),
            Concept("sci_energy_types", "Types of Energy", "science", 4, 0.4, ["sci_forces_motion"], "Learn about different forms of energy", ["Identify forms of energy", "Describe energy transformations"], 25, ["physical science", "energy"]),
            Concept("sci_electricity", "Electricity", "science", 4, 0.45, ["sci_energy_types"], "Understand basic electricity", ["Describe simple circuits", "Identify conductors and insulators"], 25, ["physical science", "energy"]),
            Concept("sci_magnetism", "Magnetism", "science", 3, 0.3, ["sci_forces_motion"], "Understand magnets and magnetic fields", ["Describe magnetic poles", "Identify magnetic materials"], 20, ["physical science"]),
            Concept("sci_sound", "Sound", "science", 3, 0.3, ["sci_energy_types"], "Understand how sound works", ["Describe how sound travels", "Explain pitch and volume"], 20, ["physical science", "waves"]),
            Concept("sci_light", "Light", "science", 4, 0.4, ["sci_energy_types"], "Understand how light works", ["Describe reflection and refraction", "Explain how we see color"], 25, ["physical science", "waves"]),
            Concept("sci_human_body", "Human Body Systems", "science", 4, 0.45, ["sci_living_things", "sci_animals_basics"], "Learn about body systems", ["Describe major body systems", "Explain how organs work together"], 30, ["biology", "human body"]),
            Concept("sci_cells", "Cells", "science", 5, 0.55, ["sci_human_body"], "Understand basic cell structure", ["Identify cell parts", "Compare plant and animal cells"], 25, ["biology", "cells"]),
            Concept("sci_heredity", "Heredity and Traits", "science", 5, 0.55, ["sci_cells"], "Understand inherited traits", ["Describe dominant and recessive traits", "Explain basic genetics"], 30, ["biology", "genetics"]),
            Concept("sci_adaptation", "Adaptation and Evolution", "science", 5, 0.6, ["sci_habitats", "sci_heredity"], "Understand how species change over time", ["Describe adaptations", "Explain natural selection basics"], 30, ["biology", "evolution"]),
            Concept("sci_chemical_changes", "Chemical Changes", "science", 5, 0.55, ["sci_mixtures"], "Understand chemical reactions", ["Identify signs of chemical change", "Describe common chemical reactions"], 25, ["physical science", "chemistry"]),
            Concept("sci_earth_resources", "Earth's Resources", "science", 4, 0.4, ["sci_rocks_minerals", "sci_water_cycle"], "Understand natural resources", ["Identify renewable and nonrenewable resources", "Describe conservation"], 25, ["earth science", "environment"]),
            Concept("sci_climate", "Climate and Biomes", "science", 5, 0.5, ["sci_weather", "sci_habitats"], "Understand climate zones and biomes", ["Compare climate and weather", "Describe major biomes"], 30, ["earth science", "ecology"]),
            Concept("sci_gravity", "Gravity", "science", 5, 0.5, ["sci_forces_motion", "sci_solar_system"], "Understand gravity", ["Describe how gravity works", "Explain weight vs mass"], 25, ["physical science", "physics"]),
            Concept("sci_scientific_method", "Scientific Method", "science", 3, 0.3, [], "Learn how to investigate scientifically", ["Describe steps of scientific method", "Design simple experiments"], 20, ["process skills"]),
        ]
        for c in science_concepts:
            self.concepts[c.id] = c

    def _build_reading(self):
        reading_concepts = [
            Concept("read_alphabet", "Alphabet Recognition", "reading", 0, 0.1, [], "Learn letters of the alphabet", ["Identify uppercase and lowercase letters", "Recite the alphabet"], 10, ["letters", "basics"]),
            Concept("read_phonics_basic", "Basic Phonics", "reading", 0, 0.15, ["read_alphabet"], "Learn letter sounds", ["Associate letters with sounds", "Blend simple CVC words"], 15, ["phonics", "basics"]),
            Concept("read_sight_words", "Sight Words", "reading", 0, 0.15, ["read_alphabet"], "Recognize common words by sight", ["Read Dolch sight words", "Use sight words in sentences"], 10, ["vocabulary", "basics"]),
            Concept("read_cvc_words", "CVC Words", "reading", 1, 0.2, ["read_phonics_basic"], "Read consonant-vowel-consonant words", ["Decode CVC words", "Write simple CVC words"], 15, ["phonics", "decoding"]),
            Concept("read_blends", "Consonant Blends", "reading", 1, 0.25, ["read_cvc_words"], "Read words with consonant blends", ["Identify blends like bl, cr, st", "Read words with beginning and ending blends"], 15, ["phonics", "decoding"]),
            Concept("read_digraphs", "Digraphs", "reading", 1, 0.25, ["read_cvc_words"], "Read words with digraphs", ["Identify sh, ch, th, wh", "Read words with digraphs"], 15, ["phonics", "decoding"]),
            Concept("read_long_vowels", "Long Vowel Patterns", "reading", 2, 0.3, ["read_blends", "read_digraphs"], "Read words with long vowel sounds", ["Identify silent-e pattern", "Read vowel team words"], 20, ["phonics", "decoding"]),
            Concept("read_fluency", "Reading Fluency", "reading", 2, 0.3, ["read_long_vowels", "read_sight_words"], "Read smoothly and with expression", ["Read grade-level text fluently", "Use proper pacing and expression"], 20, ["fluency"]),
            Concept("read_vocabulary", "Vocabulary Building", "reading", 2, 0.3, ["read_fluency"], "Learn new words and meanings", ["Use context clues", "Learn word families and roots"], 20, ["vocabulary"]),
            Concept("read_comprehension_basic", "Basic Comprehension", "reading", 1, 0.2, ["read_cvc_words", "read_sight_words"], "Understand what you read", ["Answer who, what, where questions", "Retell a story in order"], 15, ["comprehension"]),
            Concept("read_main_idea", "Main Idea and Details", "reading", 2, 0.3, ["read_comprehension_basic"], "Find the main idea of a text", ["Identify main idea", "Find supporting details"], 20, ["comprehension"]),
            Concept("read_sequence", "Sequence of Events", "reading", 2, 0.3, ["read_comprehension_basic"], "Understand story order", ["Identify beginning, middle, end", "Use sequence words"], 15, ["comprehension"]),
            Concept("read_characters", "Character Analysis", "reading", 3, 0.35, ["read_main_idea"], "Analyze story characters", ["Describe character traits", "Explain character motivations"], 20, ["comprehension", "literature"]),
            Concept("read_setting", "Setting", "reading", 2, 0.25, ["read_comprehension_basic"], "Identify and describe settings", ["Describe where and when a story takes place", "Explain how setting affects the story"], 15, ["comprehension", "literature"]),
            Concept("read_cause_effect", "Cause and Effect", "reading", 3, 0.35, ["read_main_idea"], "Identify cause and effect relationships", ["Find cause and effect in text", "Use signal words"], 20, ["comprehension"]),
            Concept("read_compare_contrast", "Compare and Contrast", "reading", 3, 0.35, ["read_main_idea"], "Compare and contrast information", ["Use Venn diagrams", "Identify similarities and differences"], 20, ["comprehension"]),
            Concept("read_inference", "Making Inferences", "reading", 3, 0.4, ["read_main_idea", "read_characters"], "Read between the lines", ["Make predictions", "Draw conclusions from clues"], 25, ["comprehension", "critical thinking"]),
            Concept("read_nonfiction", "Nonfiction Text Features", "reading", 3, 0.35, ["read_main_idea"], "Use nonfiction text features", ["Use headings and captions", "Read charts and diagrams"], 20, ["nonfiction"]),
            Concept("read_fact_opinion", "Fact vs Opinion", "reading", 3, 0.35, ["read_nonfiction"], "Distinguish facts from opinions", ["Identify factual statements", "Recognize opinion words"], 20, ["critical thinking"]),
            Concept("read_summary", "Summarizing", "reading", 4, 0.45, ["read_main_idea", "read_sequence"], "Write effective summaries", ["Identify key points", "Write concise summaries"], 25, ["comprehension", "writing"]),
            Concept("read_theme", "Theme", "reading", 4, 0.45, ["read_characters", "read_inference"], "Identify themes in literature", ["Determine the theme of a story", "Support theme with evidence"], 25, ["comprehension", "literature"]),
            Concept("read_figurative_lang", "Figurative Language", "reading", 4, 0.5, ["read_vocabulary", "read_inference"], "Understand figurative language", ["Identify similes and metaphors", "Interpret idioms"], 25, ["vocabulary", "literature"]),
            Concept("read_point_of_view", "Point of View", "reading", 4, 0.45, ["read_characters", "read_nonfiction"], "Understand narrative perspective", ["Identify first and third person", "Compare different perspectives"], 25, ["comprehension", "literature"]),
            Concept("read_text_structure", "Text Structure", "reading", 4, 0.5, ["read_nonfiction", "read_cause_effect", "read_compare_contrast"], "Identify how texts are organized", ["Identify organizational patterns", "Use text structure to comprehend"], 25, ["comprehension", "nonfiction"]),
            Concept("read_argument", "Analyzing Arguments", "reading", 5, 0.6, ["read_fact_opinion", "read_text_structure"], "Evaluate arguments in text", ["Identify claims and evidence", "Evaluate argument strength"], 30, ["critical thinking"]),
            Concept("read_poetry", "Poetry", "reading", 3, 0.4, ["read_fluency", "read_vocabulary"], "Read and understand poetry", ["Identify rhyme and rhythm", "Interpret poems"], 20, ["literature", "poetry"]),
            Concept("read_genre", "Literary Genres", "reading", 3, 0.35, ["read_comprehension_basic"], "Identify different genres", ["Distinguish fiction from nonfiction", "Identify fantasy, mystery, etc."], 15, ["literature"]),
            Concept("read_context_clues", "Context Clues", "reading", 3, 0.35, ["read_vocabulary"], "Use context to determine meaning", ["Identify context clue types", "Define unknown words using context"], 20, ["vocabulary"]),
            Concept("read_root_words", "Root Words and Affixes", "reading", 4, 0.45, ["read_vocabulary", "read_context_clues"], "Understand word parts", ["Identify prefixes, suffixes, roots", "Use word parts to determine meaning"], 25, ["vocabulary", "word study"]),
            Concept("read_research", "Research Skills", "reading", 5, 0.55, ["read_nonfiction", "read_argument"], "Conduct basic research", ["Evaluate sources", "Take notes and organize information"], 30, ["research", "nonfiction"]),
        ]
        for c in reading_concepts:
            self.concepts[c.id] = c

    def _build_coding(self):
        coding_concepts = [
            Concept("code_what_is", "What is Coding?", "coding", 0, 0.1, [], "Introduction to coding concepts", ["Understand what code is", "Know that computers follow instructions"], 10, ["basics", "intro"]),
            Concept("code_sequences", "Sequences", "coding", 0, 0.15, ["code_what_is"], "Understand step-by-step instructions", ["Create a sequence of commands", "Follow instructions in order"], 15, ["basics", "sequencing"]),
            Concept("code_patterns", "Patterns in Code", "coding", 1, 0.2, ["code_sequences"], "Recognize and create patterns", ["Identify repeating patterns", "Create pattern-based instructions"], 15, ["patterns", "basics"]),
            Concept("code_loops_intro", "Introduction to Loops", "coding", 1, 0.25, ["code_sequences"], "Understand repeating instructions", ["Use repeat blocks", "Identify when to use loops"], 20, ["loops", "control flow"]),
            Concept("code_loops_counting", "Counting Loops", "coding", 2, 0.3, ["code_loops_intro"], "Use loops with counts", ["Create for-loops with specific counts", "Predict loop output"], 20, ["loops", "control flow"]),
            Concept("code_conditionals_intro", "Introduction to Conditionals", "coding", 2, 0.3, ["code_sequences"], "Make decisions in code", ["Use if-then statements", "Understand true/false conditions"], 20, ["conditionals", "control flow"]),
            Concept("code_conditionals_else", "If-Else Statements", "coding", 2, 0.35, ["code_conditionals_intro"], "Handle two possible outcomes", ["Use if-else statements", "Create branching logic"], 20, ["conditionals", "control flow"]),
            Concept("code_variables_intro", "Introduction to Variables", "coding", 3, 0.35, ["code_sequences"], "Store and use data", ["Create and name variables", "Update variable values"], 25, ["variables", "data"]),
            Concept("code_variables_types", "Data Types", "coding", 3, 0.4, ["code_variables_intro"], "Understand different data types", ["Distinguish numbers, strings, booleans", "Choose appropriate data types"], 25, ["variables", "data"]),
            Concept("code_operators", "Operators", "coding", 3, 0.4, ["code_variables_intro"], "Use math and comparison operators", ["Use arithmetic operators", "Use comparison operators"], 20, ["operators", "math"]),
            Concept("code_functions_intro", "Introduction to Functions", "coding", 3, 0.45, ["code_sequences", "code_loops_intro"], "Create reusable code blocks", ["Define simple functions", "Call functions"], 25, ["functions"]),
            Concept("code_functions_params", "Functions with Parameters", "coding", 4, 0.5, ["code_functions_intro", "code_variables_intro"], "Pass information to functions", ["Define functions with parameters", "Return values from functions"], 30, ["functions"]),
            Concept("code_events", "Events", "coding", 2, 0.3, ["code_sequences"], "Respond to user actions", ["Use event handlers", "Create interactive programs"], 20, ["events", "interactive"]),
            Concept("code_debugging", "Debugging", "coding", 2, 0.3, ["code_sequences"], "Find and fix errors in code", ["Identify common bugs", "Use systematic debugging"], 20, ["debugging", "problem solving"]),
            Concept("code_lists_intro", "Introduction to Lists", "coding", 4, 0.45, ["code_variables_types"], "Store collections of data", ["Create and access lists", "Add and remove items"], 25, ["data structures"]),
            Concept("code_lists_operations", "List Operations", "coding", 4, 0.5, ["code_lists_intro", "code_loops_counting"], "Work with list data", ["Loop through lists", "Search and sort lists"], 30, ["data structures"]),
            Concept("code_strings", "String Operations", "coding", 4, 0.45, ["code_variables_types"], "Manipulate text data", ["Concatenate strings", "Access characters in strings"], 25, ["strings", "data"]),
            Concept("code_nested_loops", "Nested Loops", "coding", 4, 0.55, ["code_loops_counting"], "Use loops inside loops", ["Create nested loop patterns", "Understand loop complexity"], 30, ["loops", "control flow"]),
            Concept("code_algorithms_search", "Search Algorithms", "coding", 5, 0.6, ["code_lists_operations", "code_loops_counting"], "Find items in data", ["Implement linear search", "Understand binary search concept"], 30, ["algorithms"]),
            Concept("code_algorithms_sort", "Sorting Algorithms", "coding", 5, 0.65, ["code_lists_operations", "code_nested_loops"], "Arrange data in order", ["Implement bubble sort", "Compare sorting methods"], 35, ["algorithms"]),
            Concept("code_recursion", "Recursion", "coding", 6, 0.7, ["code_functions_params"], "Functions that call themselves", ["Understand base cases", "Write simple recursive functions"], 35, ["recursion", "functions"]),
            Concept("code_oop_intro", "Object-Oriented Basics", "coding", 5, 0.6, ["code_functions_params", "code_variables_types"], "Introduction to objects and classes", ["Create simple classes", "Understand objects as instances"], 30, ["OOP"]),
            Concept("code_oop_inheritance", "Inheritance", "coding", 6, 0.7, ["code_oop_intro"], "Extend classes with inheritance", ["Create child classes", "Override methods"], 35, ["OOP"]),
            Concept("code_dictionaries", "Dictionaries", "coding", 5, 0.55, ["code_variables_types", "code_lists_intro"], "Store key-value pairs", ["Create and access dictionaries", "Iterate over key-value pairs"], 30, ["data structures"]),
            Concept("code_file_io", "File Input/Output", "coding", 5, 0.55, ["code_strings", "code_variables_types"], "Read and write files", ["Open and read files", "Write data to files"], 30, ["IO", "files"]),
            Concept("code_error_handling", "Error Handling", "coding", 5, 0.6, ["code_debugging", "code_functions_params"], "Handle errors gracefully", ["Use try-except blocks", "Raise custom errors"], 30, ["error handling"]),
            Concept("code_web_basics", "Web Development Basics", "coding", 5, 0.6, ["code_strings", "code_functions_params"], "Introduction to HTML and web", ["Create basic HTML pages", "Understand client-server model"], 35, ["web", "HTML"]),
            Concept("code_apis", "Working with APIs", "coding", 6, 0.7, ["code_web_basics", "code_dictionaries"], "Fetch data from web services", ["Make API requests", "Parse JSON responses"], 35, ["web", "APIs"]),
            Concept("code_project_planning", "Project Planning", "coding", 4, 0.45, ["code_functions_intro", "code_debugging"], "Plan and organize coding projects", ["Break problems into steps", "Create pseudocode"], 25, ["planning", "problem solving"]),
            Concept("code_game_design", "Game Design Basics", "coding", 4, 0.5, ["code_events", "code_conditionals_else", "code_loops_counting"], "Create simple games", ["Design game mechanics", "Implement game logic"], 35, ["games", "creative"]),
        ]
        for c in coding_concepts:
            self.concepts[c.id] = c

    def _build_edges(self):
        self.edges = []
        for concept in self.concepts.values():
            for prereq_id in concept.prerequisites:
                if prereq_id in self.concepts:
                    self.edges.append(Edge(source=prereq_id, target=concept.id, relationship="prerequisite"))

    def get_knowledge_graph(self, subject: str, grade: Optional[int] = None) -> Dict[str, Any]:
        nodes = []
        for c in self.concepts.values():
            if c.subject != subject:
                continue
            if grade is not None and c.grade_level > grade:
                continue
            nodes.append({
                "id": c.id,
                "name": c.name,
                "subject": c.subject,
                "grade_level": c.grade_level,
                "difficulty": c.difficulty,
                "description": c.description,
                "learning_objectives": c.learning_objectives,
                "estimated_minutes": c.estimated_minutes,
                "tags": c.tags,
                "prerequisites": c.prerequisites,
            })

        node_ids = {n["id"] for n in nodes}
        edges = []
        for e in self.edges:
            if e.source in node_ids and e.target in node_ids:
                edges.append({
                    "source": e.source,
                    "target": e.target,
                    "relationship": e.relationship,
                    "weight": e.weight,
                })

        return {"subject": subject, "grade": grade, "nodes": nodes, "edges": edges}

    def get_lessons(self, subject: str, grade: Optional[int] = None) -> List[Dict[str, Any]]:
        lessons = []
        for c in self.concepts.values():
            if c.subject != subject:
                continue
            if grade is not None and c.grade_level != grade:
                continue
            lessons.append({
                "lesson_id": c.id,
                "title": c.name,
                "subject": c.subject,
                "grade_level": c.grade_level,
                "difficulty": c.difficulty,
                "description": c.description,
                "learning_objectives": c.learning_objectives,
                "estimated_minutes": c.estimated_minutes,
                "tags": c.tags,
                "prerequisites": c.prerequisites,
            })
        lessons.sort(key=lambda x: (x["grade_level"], x["difficulty"]))
        return lessons

    def get_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        c = self.concepts.get(lesson_id)
        if not c:
            return None
        exercises = self._generate_exercises(c)
        content = self._generate_lesson_content(c)
        return {
            "lesson_id": c.id,
            "title": c.name,
            "subject": c.subject,
            "grade_level": c.grade_level,
            "difficulty": c.difficulty,
            "description": c.description,
            "learning_objectives": c.learning_objectives,
            "estimated_minutes": c.estimated_minutes,
            "tags": c.tags,
            "prerequisites": c.prerequisites,
            "content": content,
            "exercises": exercises,
        }

    def _generate_lesson_content(self, concept: Concept) -> Dict[str, Any]:
        return {
            "introduction": f"Welcome to the lesson on **{concept.name}**! {concept.description}.",
            "sections": [
                {"title": "What You'll Learn", "body": "In this lesson, you'll learn:\n" + "\n".join(f"- {obj}" for obj in concept.learning_objectives)},
                {"title": "Key Concepts", "body": f"Let's explore the key ideas behind {concept.name.lower()}. This topic is part of {concept.subject} and is designed for grade {concept.grade_level} learners."},
                {"title": "Practice Time", "body": "Now that you've learned the concepts, let's put your knowledge to the test with some practice exercises!"},
            ],
            "summary": f"Great job learning about {concept.name.lower()}! Remember to review these concepts regularly.",
        }

    def _generate_exercises(self, concept: Concept) -> List[Dict[str, Any]]:
        exercises = []
        if concept.subject == "math":
            exercises = self._math_exercises(concept)
        elif concept.subject == "science":
            exercises = self._science_exercises(concept)
        elif concept.subject == "reading":
            exercises = self._reading_exercises(concept)
        elif concept.subject == "coding":
            exercises = self._coding_exercises(concept)
        return exercises

    def _math_exercises(self, concept: Concept) -> List[Dict[str, Any]]:
        base = [
            {"id": f"{concept.id}_ex1", "type": "multiple_choice", "question": f"Which of the following best describes {concept.name.lower()}?", "options": [concept.learning_objectives[0] if concept.learning_objectives else "Correct answer", "An unrelated concept", "Something completely different", "None of the above"], "correct_answer": 0, "difficulty": concept.difficulty, "hint": f"Think about what {concept.name.lower()} means."},
            {"id": f"{concept.id}_ex2", "type": "true_false", "question": f"{concept.name} is an important skill in {concept.subject}.", "correct_answer": True, "difficulty": concept.difficulty * 0.8, "hint": "Think about how this concept relates to other math skills."},
            {"id": f"{concept.id}_ex3", "type": "short_answer", "question": f"Explain in your own words what {concept.name.lower()} means.", "sample_answer": concept.description, "difficulty": concept.difficulty * 1.2, "hint": "Try to use simple language."},
        ]
        return base

    def _science_exercises(self, concept: Concept) -> List[Dict[str, Any]]:
        return [
            {"id": f"{concept.id}_ex1", "type": "multiple_choice", "question": f"What is the main idea behind {concept.name.lower()}?", "options": [concept.description, "Something about math", "A type of animal", "A cooking technique"], "correct_answer": 0, "difficulty": concept.difficulty, "hint": "Read the lesson introduction again."},
            {"id": f"{concept.id}_ex2", "type": "true_false", "question": f"{concept.name} is a topic in science.", "correct_answer": True, "difficulty": concept.difficulty * 0.8, "hint": "This is a science lesson!"},
            {"id": f"{concept.id}_ex3", "type": "short_answer", "question": f"Give one example related to {concept.name.lower()}.", "sample_answer": f"An example of {concept.name.lower()} is: {concept.learning_objectives[0] if concept.learning_objectives else 'a real-world application'}.", "difficulty": concept.difficulty * 1.1, "hint": "Think about examples from everyday life."},
        ]

    def _reading_exercises(self, concept: Concept) -> List[Dict[str, Any]]:
        return [
            {"id": f"{concept.id}_ex1", "type": "multiple_choice", "question": f"What skill does '{concept.name}' help you develop?", "options": [concept.learning_objectives[0] if concept.learning_objectives else "Better reading", "Better swimming", "Better cooking", "Better drawing"], "correct_answer": 0, "difficulty": concept.difficulty, "hint": "Think about reading skills."},
            {"id": f"{concept.id}_ex2", "type": "true_false", "question": f"'{concept.name}' is a reading and language arts skill.", "correct_answer": True, "difficulty": concept.difficulty * 0.8, "hint": "What subject are we studying?"},
            {"id": f"{concept.id}_ex3", "type": "short_answer", "question": f"Why is {concept.name.lower()} important for reading?", "sample_answer": concept.description, "difficulty": concept.difficulty * 1.2, "hint": "Think about how this helps you understand text."},
        ]

    def _coding_exercises(self, concept: Concept) -> List[Dict[str, Any]]:
        return [
            {"id": f"{concept.id}_ex1", "type": "multiple_choice", "question": f"What is {concept.name.lower()} in coding?", "options": [concept.description, "A type of computer hardware", "A social media platform", "A type of video game"], "correct_answer": 0, "difficulty": concept.difficulty, "hint": "Think about programming concepts."},
            {"id": f"{concept.id}_ex2", "type": "true_false", "question": f"{concept.name} is a concept used in programming.", "correct_answer": True, "difficulty": concept.difficulty * 0.8, "hint": "This is a coding lesson!"},
            {"id": f"{concept.id}_ex3", "type": "short_answer", "question": f"When would you use {concept.name.lower()} in a program?", "sample_answer": concept.description, "difficulty": concept.difficulty * 1.2, "hint": "Think about real coding scenarios."},
        ]

    def recommend_lessons(self, subject: str, mastery_data: Dict[str, float], grade: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        candidates = []
        for c in self.concepts.values():
            if c.subject != subject:
                continue
            if grade is not None and c.grade_level > grade + 1:
                continue

            current_mastery = mastery_data.get(c.id, 0.0)
            if current_mastery >= 0.9:
                continue

            prereqs_met = all(mastery_data.get(p, 0.0) >= 0.5 for p in c.prerequisites)
            if not prereqs_met and c.prerequisites:
                continue

            priority = 0.0
            if 0.3 <= current_mastery < 0.9:
                priority += 0.4
            elif current_mastery < 0.3:
                priority += 0.2

            avg_prereq = sum(mastery_data.get(p, 0.0) for p in c.prerequisites) / max(len(c.prerequisites), 1)
            priority += avg_prereq * 0.3

            dependents = sum(1 for other in self.concepts.values() if c.id in other.prerequisites)
            priority += min(dependents * 0.05, 0.3)

            candidates.append({
                "lesson_id": c.id,
                "title": c.name,
                "subject": c.subject,
                "grade_level": c.grade_level,
                "difficulty": c.difficulty,
                "current_mastery": current_mastery,
                "priority_score": round(priority, 3),
                "reason": self._recommendation_reason(c, current_mastery, avg_prereq),
                "estimated_minutes": c.estimated_minutes,
            })

        candidates.sort(key=lambda x: x["priority_score"], reverse=True)
        return candidates[:limit]

    def _recommendation_reason(self, concept: Concept, mastery: float, prereq_mastery: float) -> str:
        if mastery < 0.1:
            return f"New concept ready to learn — prerequisites are solid."
        elif mastery < 0.5:
            return f"You've started learning this — keep practicing to build mastery."
        elif mastery < 0.9:
            return f"Almost mastered — a few more practice sessions will solidify your understanding."
        return "Review to maintain mastery."

    def get_learning_path(self, subject: str, start_concept: str, target_concept: str) -> List[str]:
        if start_concept not in self.concepts or target_concept not in self.concepts:
            return []
        adjacency: Dict[str, List[str]] = {}
        for e in self.edges:
            if e.source not in adjacency:
                adjacency[e.source] = []
            adjacency[e.source].append(e.target)

        from collections import deque
        visited = set()
        queue = deque([(start_concept, [start_concept])])
        visited.add(start_concept)

        while queue:
            current, path = queue.popleft()
            if current == target_concept:
                return path
            for neighbor in adjacency.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []


knowledge_graph = KnowledgeGraph()

__all__ = ["KnowledgeGraph", "knowledge_graph", "Concept", "Edge"]
