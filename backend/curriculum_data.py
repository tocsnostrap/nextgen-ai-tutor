import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .core.database import CurriculumStandard

logger = logging.getLogger(__name__)

CURRICULUM = []

def _s(subject, grade, strand, seq, sid, title, desc, objectives, hours=2.0, prereqs=None, activities=None):
    CURRICULUM.append({
        "id": f"{subject}_g{grade}_{sid}",
        "subject": subject,
        "grade_level": grade,
        "strand": strand,
        "title": title,
        "description": desc,
        "learning_objectives": objectives,
        "estimated_hours": hours,
        "sequence_order": seq,
        "prerequisites": prereqs or [],
        "activity_types": activities or ["lesson", "practice", "game"],
    })


_s("math", 0, "Counting & Cardinality", 1, "counting", "Counting to 20",
   "Learn to count objects from 1 to 20, understand one-to-one correspondence.",
   ["Count to 20 by ones", "Count objects in a set", "Understand that each number refers to one more"], 3.0,
   activities=["lesson", "practice", "game", "video"])

_s("math", 0, "Counting & Cardinality", 2, "comparing", "Comparing Numbers",
   "Compare groups of objects to determine which has more, fewer, or the same amount.",
   ["Compare two groups using more/fewer/same", "Use matching to compare quantities"], 2.0,
   prereqs=["math_g0_counting"])

_s("math", 0, "Geometry", 3, "shapes_basic", "Basic Shapes",
   "Identify and describe circles, squares, triangles, and rectangles in the environment.",
   ["Name basic 2D shapes", "Find shapes in real objects", "Describe shape attributes"], 2.5)

_s("math", 0, "Measurement", 4, "measurement_k", "Big and Small",
   "Compare objects by measurable attributes like length, height, and weight.",
   ["Compare two objects by length", "Use words like taller/shorter/heavier/lighter"], 1.5)

_s("math", 1, "Operations", 1, "addition_basic", "Addition Within 10",
   "Add numbers with sums up to 10 using objects, drawings, and equations.",
   ["Solve addition problems within 10", "Use objects and pictures to add", "Write addition equations"], 4.0,
   prereqs=["math_g0_counting"], activities=["lesson", "practice", "game"])

_s("math", 1, "Operations", 2, "subtraction_basic", "Subtraction Within 10",
   "Subtract numbers within 10 using objects, drawings, and equations.",
   ["Solve subtraction problems within 10", "Understand subtraction as taking away", "Write subtraction equations"], 4.0,
   prereqs=["math_g1_addition_basic"])

_s("math", 1, "Operations", 3, "add_sub_20", "Addition and Subtraction Within 20",
   "Extend addition and subtraction skills to numbers within 20.",
   ["Add and subtract within 20", "Use strategies like counting on", "Solve word problems"], 5.0,
   prereqs=["math_g1_addition_basic", "math_g1_subtraction_basic"])

_s("math", 1, "Number Sense", 4, "place_value_tens", "Tens and Ones",
   "Understand that two-digit numbers are made of tens and ones.",
   ["Bundle objects into groups of 10", "Represent numbers as tens and ones", "Compare two-digit numbers"], 3.0,
   prereqs=["math_g1_add_sub_20"])

_s("math", 2, "Operations", 1, "addition_100", "Addition Within 100",
   "Add two-digit numbers using strategies based on place value.",
   ["Add within 100 using place value", "Use number lines and base-ten blocks", "Solve two-step word problems"], 5.0,
   prereqs=["math_g1_place_value_tens"])

_s("math", 2, "Operations", 2, "subtraction_100", "Subtraction Within 100",
   "Subtract two-digit numbers with and without regrouping.",
   ["Subtract within 100", "Use regrouping strategies", "Check subtraction with addition"], 5.0,
   prereqs=["math_g2_addition_100"])

_s("math", 2, "Measurement", 3, "measurement_2", "Measuring Length",
   "Measure and estimate lengths using standard units (inches, centimeters).",
   ["Measure objects with a ruler", "Estimate lengths", "Compare measurements"], 3.0)

_s("math", 2, "Data", 4, "data_graphs", "Picture Graphs and Bar Graphs",
   "Collect data, create graphs, and answer questions about data.",
   ["Create picture and bar graphs", "Read and interpret graphs", "Compare data categories"], 2.5)

_s("math", 3, "Operations", 1, "multiplication_intro", "Introduction to Multiplication",
   "Understand multiplication as equal groups and repeated addition.",
   ["Model multiplication with arrays", "Multiply within 5x5", "Understand the commutative property"], 6.0,
   prereqs=["math_g2_addition_100"], activities=["lesson", "practice", "game", "video"])

_s("math", 3, "Operations", 2, "division_intro", "Introduction to Division",
   "Understand division as sharing equally and as the inverse of multiplication.",
   ["Divide objects into equal groups", "Relate division to multiplication", "Solve division within 50"], 5.0,
   prereqs=["math_g3_multiplication_intro"])

_s("math", 3, "Fractions", 3, "fractions_intro", "Understanding Fractions",
   "Understand fractions as parts of a whole, focusing on unit fractions.",
   ["Identify fractions on a number line", "Compare fractions with same denominator", "Understand numerator and denominator"], 5.0,
   prereqs=["math_g3_division_intro"])

_s("math", 3, "Measurement", 4, "time_elapsed", "Telling Time and Elapsed Time",
   "Tell time to the nearest minute and solve problems involving elapsed time.",
   ["Read analog and digital clocks", "Calculate elapsed time", "Solve time word problems"], 3.0)

_s("math", 4, "Operations", 1, "multi_digit_mult", "Multi-Digit Multiplication",
   "Multiply multi-digit numbers using the standard algorithm.",
   ["Multiply up to 4-digit by 1-digit", "Multiply 2-digit by 2-digit", "Estimate products"], 6.0,
   prereqs=["math_g3_multiplication_intro"])

_s("math", 4, "Operations", 2, "long_division", "Long Division",
   "Divide multi-digit numbers by one-digit divisors with remainders.",
   ["Perform long division", "Interpret remainders in context", "Check division with multiplication"], 6.0,
   prereqs=["math_g3_division_intro", "math_g4_multi_digit_mult"])

_s("math", 4, "Fractions", 3, "fractions_equiv", "Equivalent Fractions and Ordering",
   "Generate equivalent fractions, compare and order fractions.",
   ["Find equivalent fractions", "Compare fractions with different denominators", "Order fractions on a number line"], 5.0,
   prereqs=["math_g3_fractions_intro"])

_s("math", 4, "Decimals", 4, "decimals_intro", "Introduction to Decimals",
   "Understand decimal notation for fractions with denominators of 10 and 100.",
   ["Read and write decimals to hundredths", "Convert between fractions and decimals", "Compare decimals"], 4.0,
   prereqs=["math_g4_fractions_equiv"])

_s("math", 5, "Fractions", 1, "fraction_operations", "Fraction Operations",
   "Add, subtract, multiply, and divide fractions and mixed numbers.",
   ["Add and subtract fractions with unlike denominators", "Multiply fractions", "Divide unit fractions by whole numbers"], 8.0,
   prereqs=["math_g4_fractions_equiv"])

_s("math", 5, "Decimals", 2, "decimal_operations", "Decimal Operations",
   "Perform all four operations with decimals to hundredths.",
   ["Add and subtract decimals", "Multiply decimals", "Divide decimals"], 6.0,
   prereqs=["math_g4_decimals_intro"])

_s("math", 5, "Geometry", 3, "volume", "Volume and 3D Shapes",
   "Understand volume as an attribute of solid figures and calculate it.",
   ["Find volume using unit cubes", "Apply volume formulas for rectangular prisms", "Solve real-world volume problems"], 4.0)

_s("math", 5, "Coordinate", 4, "coordinate_plane", "Coordinate Plane",
   "Graph points on a coordinate plane and interpret coordinate values.",
   ["Plot ordered pairs", "Identify coordinates of points", "Solve problems using coordinate graphs"], 3.0)

_s("math", 6, "Ratios", 1, "ratios", "Ratios and Proportional Relationships",
   "Understand ratio concepts and use ratio reasoning to solve problems.",
   ["Write and interpret ratios", "Find equivalent ratios", "Solve proportion problems"], 6.0,
   prereqs=["math_g5_fraction_operations"])

_s("math", 6, "Expressions", 2, "expressions_equations", "Expressions and Equations",
   "Write, evaluate, and solve one-variable expressions and equations.",
   ["Write algebraic expressions", "Evaluate expressions with variables", "Solve one-step equations"], 7.0,
   prereqs=["math_g5_decimal_operations"])

_s("math", 6, "Statistics", 3, "statistics_intro", "Introduction to Statistics",
   "Develop understanding of statistical variability and data distributions.",
   ["Calculate mean, median, and mode", "Create and interpret dot plots and histograms", "Understand data variability"], 4.0)

_s("math", 6, "Geometry", 4, "area_surface", "Area and Surface Area",
   "Find area of polygons and surface area of 3D figures.",
   ["Calculate area of triangles and quadrilaterals", "Find surface area using nets", "Solve composite figure problems"], 5.0,
   prereqs=["math_g5_volume"])


_s("reading", 0, "Phonics", 1, "letter_recognition", "Letter Recognition",
   "Recognize and name all upper and lowercase letters of the alphabet.",
   ["Identify uppercase letters", "Identify lowercase letters", "Match upper to lowercase"], 4.0,
   activities=["lesson", "practice", "game"])

_s("reading", 0, "Phonics", 2, "letter_sounds", "Letter Sounds",
   "Associate each letter with its most common sound.",
   ["Say the sound for each consonant", "Say short vowel sounds", "Match letters to beginning sounds in words"], 5.0,
   prereqs=["reading_g0_letter_recognition"])

_s("reading", 0, "Concepts of Print", 3, "print_concepts", "How Books Work",
   "Understand basic features of print including directionality and word spacing.",
   ["Identify front cover, back cover, and title", "Track words left to right, top to bottom", "Understand that words are separated by spaces"], 2.0)

_s("reading", 0, "Comprehension", 4, "story_elements_k", "Story Time",
   "Listen to stories and identify key details including characters and events.",
   ["Identify main characters", "Retell key events in order", "Ask and answer questions about a story"], 3.0)

_s("reading", 1, "Phonics", 1, "phonics_blends", "Blends and Digraphs",
   "Decode words with consonant blends (bl, cr, st) and digraphs (sh, ch, th).",
   ["Read words with initial blends", "Read words with digraphs", "Distinguish between blends and digraphs"], 5.0,
   prereqs=["reading_g0_letter_sounds"])

_s("reading", 1, "Fluency", 2, "sight_words", "Sight Words",
   "Recognize and read high-frequency sight words automatically.",
   ["Read 100 common sight words", "Use sight words in sentences", "Identify sight words in text"], 6.0,
   prereqs=["reading_g1_phonics_blends"])

_s("reading", 1, "Fluency", 3, "fluency_1", "Reading Fluently",
   "Read grade-level text with accuracy, appropriate rate, and expression.",
   ["Read aloud with expression", "Self-correct when reading doesn't make sense", "Reread for fluency practice"], 5.0,
   prereqs=["reading_g1_sight_words"])

_s("reading", 1, "Comprehension", 4, "retelling", "Retelling Stories",
   "Retell stories including key details and demonstrate understanding of the central message.",
   ["Retell beginning, middle, and end", "Identify the central message or lesson", "Describe characters and settings"], 3.0,
   prereqs=["reading_g1_fluency_1"])

_s("reading", 2, "Vocabulary", 1, "vocabulary_context", "Words in Context",
   "Determine the meaning of unknown words using context clues and word parts.",
   ["Use sentence clues to figure out word meanings", "Identify prefixes and suffixes", "Use a glossary or dictionary"], 4.0,
   prereqs=["reading_g1_fluency_1"])

_s("reading", 2, "Comprehension", 2, "comprehension_2", "Reading Comprehension",
   "Ask and answer questions about key details in a text to demonstrate understanding.",
   ["Identify main topic and key details", "Ask who, what, where, when, why questions", "Summarize paragraphs"], 5.0,
   prereqs=["reading_g2_vocabulary_context"])

_s("reading", 2, "Writing Connection", 3, "text_features", "Text Features",
   "Use text features like headings, bold words, and captions to locate information.",
   ["Identify and use headings and subheadings", "Interpret bold and italic words", "Read captions, labels, and diagrams"], 2.5)

_s("reading", 2, "Literature", 4, "poetry_intro", "Introduction to Poetry",
   "Read and respond to poems, identifying rhyme, rhythm, and imagery.",
   ["Identify rhyming words", "Clap syllables and rhythm", "Describe images created by words"], 2.0)

_s("reading", 3, "Comprehension", 1, "main_idea", "Main Idea and Details",
   "Determine the main idea of a text and explain how key details support it.",
   ["State the main idea in your own words", "Identify supporting details", "Distinguish main idea from topic"], 4.0,
   prereqs=["reading_g2_comprehension_2"])

_s("reading", 3, "Comprehension", 2, "inference", "Making Inferences",
   "Use evidence from the text combined with prior knowledge to make inferences.",
   ["Find text evidence to support inferences", "Distinguish between stated and implied information", "Predict outcomes based on evidence"], 5.0,
   prereqs=["reading_g3_main_idea"])

_s("reading", 3, "Vocabulary", 3, "figurative_lang_intro", "Similes and Metaphors",
   "Understand and identify basic figurative language in text.",
   ["Identify similes using like/as", "Understand simple metaphors", "Explain what figurative language means"], 3.0)

_s("reading", 3, "Literature", 4, "story_structure", "Story Structure",
   "Describe how a story's beginning introduces the problem and the ending resolves it.",
   ["Identify problem and solution", "Describe story arc: beginning, middle, climax, end", "Compare story structures across texts"], 3.0)

_s("reading", 4, "Comprehension", 1, "text_structure", "Text Structure",
   "Describe the overall structure of a text (chronology, comparison, cause/effect, problem/solution).",
   ["Identify text organization patterns", "Use signal words to determine structure", "Compare structures across texts"], 4.0,
   prereqs=["reading_g3_inference"])

_s("reading", 4, "Comprehension", 2, "point_of_view", "Point of View",
   "Compare and contrast first-person and third-person points of view.",
   ["Identify narrator's point of view", "Explain how point of view affects the story", "Compare accounts of the same event from different perspectives"], 3.0)

_s("reading", 4, "Vocabulary", 3, "figurative_lang_adv", "Idioms, Adages, and Proverbs",
   "Recognize and explain the meaning of common idioms, adages, and proverbs.",
   ["Interpret common idioms", "Explain the meaning of adages", "Use context to understand figurative expressions"], 3.0,
   prereqs=["reading_g3_figurative_lang_intro"])

_s("reading", 4, "Research", 4, "research_intro", "Introduction to Research",
   "Conduct short research projects using multiple sources.",
   ["Generate research questions", "Find information from multiple sources", "Take notes and organize findings"], 4.0)

_s("reading", 5, "Comprehension", 1, "analysis", "Analyzing Text",
   "Analyze how authors use reasons and evidence to support particular points.",
   ["Identify author's claims and evidence", "Evaluate the strength of arguments", "Compare two texts on the same topic"], 5.0,
   prereqs=["reading_g4_text_structure"])

_s("reading", 5, "Comprehension", 2, "theme", "Theme and Summary",
   "Determine the theme of a story, drama, or poem and summarize the text.",
   ["Identify recurring themes", "Support theme with text evidence", "Write objective summaries"], 4.0,
   prereqs=["reading_g5_analysis"])

_s("reading", 5, "Vocabulary", 3, "word_relationships", "Word Relationships",
   "Use the relationship between words to better understand each word.",
   ["Identify synonyms and antonyms", "Understand analogies", "Distinguish among related words (e.g., slim vs. skinny vs. thin)"], 3.0)

_s("reading", 5, "Literature", 4, "genre_study", "Genre Study",
   "Compare and contrast stories in the same genre on their approaches to similar themes and topics.",
   ["Identify genre characteristics", "Compare themes across genre", "Analyze how genre conventions affect meaning"], 3.0)

_s("reading", 6, "Comprehension", 1, "critical_reading", "Critical Reading",
   "Analyze how authors develop and contrast points of view or claims.",
   ["Evaluate author's purpose and perspective", "Analyze rhetorical techniques", "Assess credibility of sources"], 5.0,
   prereqs=["reading_g5_analysis", "reading_g5_theme"])

_s("reading", 6, "Comprehension", 2, "argument_eval", "Evaluating Arguments",
   "Trace and evaluate the argument and specific claims in a text.",
   ["Distinguish claims from evidence", "Evaluate reasoning and evidence", "Identify logical fallacies"], 4.0,
   prereqs=["reading_g6_critical_reading"])

_s("reading", 6, "Vocabulary", 3, "academic_vocab", "Academic Vocabulary",
   "Acquire and use grade-appropriate academic and domain-specific vocabulary.",
   ["Use context clues for academic words", "Understand domain-specific terminology", "Use reference materials effectively"], 4.0)

_s("reading", 6, "Literature", 4, "literary_analysis", "Literary Analysis",
   "Analyze how particular elements of a story interact (setting shapes characters or plot).",
   ["Analyze character development", "Examine how setting influences plot", "Interpret symbolic meaning"], 4.0)


_s("science", 0, "Life Science", 1, "senses", "My Five Senses",
   "Explore the five senses and how we use them to learn about the world.",
   ["Name the five senses", "Match senses to body parts", "Describe objects using senses"], 2.0,
   activities=["lesson", "practice", "video"])

_s("science", 0, "Earth Science", 2, "weather_k", "Weather and Seasons",
   "Observe and describe daily weather and seasonal changes.",
   ["Describe today's weather", "Name the four seasons", "Connect weather to what we wear"], 2.5)

_s("science", 0, "Life Science", 3, "living_nonliving", "Living and Non-Living Things",
   "Distinguish between living and non-living things based on observable characteristics.",
   ["Identify living things", "Identify non-living things", "Explain what living things need"], 2.0)

_s("science", 1, "Life Science", 1, "plants", "Plants and How They Grow",
   "Understand plant parts, needs, and life cycles.",
   ["Name parts of a plant", "Describe what plants need to grow", "Observe a plant life cycle"], 3.0,
   prereqs=["science_g0_living_nonliving"])

_s("science", 1, "Life Science", 2, "animals_basic", "Animals and Their Needs",
   "Learn about different animals, their habitats, and basic needs.",
   ["Classify animals by type", "Describe animal habitats", "Explain what animals need to survive"], 3.0)

_s("science", 1, "Physical Science", 3, "sound_light", "Sound and Light",
   "Explore how sound and light behave and how we perceive them.",
   ["Describe how sounds are made", "Explain that light travels in straight lines", "Investigate shadows"], 2.5)

_s("science", 2, "Physical Science", 1, "matter_states", "States of Matter",
   "Identify and describe solids, liquids, and gases and how matter can change states.",
   ["Classify matter as solid, liquid, or gas", "Describe properties of each state", "Observe changes between states"], 3.0,
   activities=["lesson", "practice", "game", "video"])

_s("science", 2, "Life Science", 2, "habitats", "Animal Habitats",
   "Explore different habitats and how animals are adapted to survive in them.",
   ["Name major habitat types", "Explain animal adaptations", "Describe food chains"], 3.5,
   prereqs=["science_g1_animals_basic"])

_s("science", 2, "Earth Science", 3, "earth_materials", "Rocks, Soil, and Water",
   "Investigate properties of rocks, soil, and water on Earth's surface.",
   ["Classify rocks by properties", "Describe soil composition", "Explain the water cycle basics"], 3.0)

_s("science", 3, "Physical Science", 1, "forces_motion", "Forces and Motion",
   "Investigate how forces affect the motion of objects.",
   ["Define force, push, and pull", "Predict how forces change motion", "Investigate friction and gravity"], 4.0,
   prereqs=["science_g2_matter_states"])

_s("science", 3, "Earth Science", 2, "weather_climate", "Weather and Climate",
   "Collect and analyze weather data; understand climate patterns.",
   ["Use weather instruments", "Record and graph weather data", "Distinguish weather from climate"], 3.5,
   prereqs=["science_g0_weather_k"])

_s("science", 3, "Life Science", 3, "life_cycles", "Life Cycles",
   "Compare life cycles of different organisms including metamorphosis.",
   ["Describe life cycles of plants and animals", "Compare complete and incomplete metamorphosis", "Explain inherited vs. learned traits"], 3.0,
   prereqs=["science_g1_plants"])

_s("science", 3, "Engineering", 4, "engineering_design", "Engineering Design Process",
   "Use the engineering design process to solve problems.",
   ["Define a problem", "Design and test solutions", "Improve designs based on results"], 2.5)

_s("science", 4, "Life Science", 1, "ecosystems", "Ecosystems and Food Webs",
   "Understand how organisms interact within ecosystems through food webs.",
   ["Describe producers, consumers, and decomposers", "Construct food webs", "Explain energy flow in ecosystems"], 4.0,
   prereqs=["science_g2_habitats", "science_g3_life_cycles"])

_s("science", 4, "Physical Science", 2, "energy_forms", "Forms of Energy",
   "Identify different forms of energy and how energy can be transferred.",
   ["Name forms of energy (heat, light, sound, electrical)", "Describe energy transfers", "Investigate conductors and insulators"], 4.0,
   prereqs=["science_g3_forces_motion"])

_s("science", 4, "Earth Science", 3, "earth_surface", "Earth's Changing Surface",
   "Explain how Earth's surface changes through weathering, erosion, and deposition.",
   ["Describe weathering processes", "Explain erosion and deposition", "Identify landforms created by these processes"], 3.0,
   prereqs=["science_g2_earth_materials"])

_s("science", 5, "Life Science", 1, "cells_organisms", "Cells and Organisms",
   "Understand that all living things are made of cells and how cells function.",
   ["Describe cell parts and functions", "Compare plant and animal cells", "Explain how cells form tissues and organs"], 5.0,
   prereqs=["science_g4_ecosystems"])

_s("science", 5, "Earth Science", 2, "earth_systems", "Earth's Systems",
   "Understand Earth's major systems (geosphere, hydrosphere, atmosphere, biosphere) and how they interact.",
   ["Describe the four Earth systems", "Explain interactions between systems", "Analyze the water cycle in depth"], 4.0,
   prereqs=["science_g4_earth_surface"])

_s("science", 5, "Physical Science", 3, "mixtures_solutions", "Mixtures and Solutions",
   "Investigate properties of mixtures and solutions and methods of separation.",
   ["Distinguish mixtures from solutions", "Separate mixtures using physical methods", "Describe dissolving and concentration"], 3.5,
   prereqs=["science_g2_matter_states"])

_s("science", 5, "Space", 4, "solar_system", "The Solar System",
   "Explore the sun, planets, and other objects in our solar system.",
   ["Name and order the planets", "Compare inner and outer planets", "Explain Earth's rotation and revolution"], 3.0)

_s("science", 6, "Physical Science", 1, "chemistry_basics", "Introduction to Chemistry",
   "Understand atoms, elements, and basic chemical reactions.",
   ["Describe the structure of atoms", "Read the periodic table", "Identify signs of chemical reactions"], 5.0,
   prereqs=["science_g5_mixtures_solutions"])

_s("science", 6, "Physical Science", 2, "physics_basics", "Introduction to Physics",
   "Explore Newton's laws of motion and basic physics concepts.",
   ["State Newton's three laws", "Calculate speed and velocity", "Investigate balanced and unbalanced forces"], 5.0,
   prereqs=["science_g3_forces_motion", "science_g4_energy_forms"])

_s("science", 6, "Life Science", 3, "human_body", "Human Body Systems",
   "Study major human body systems and how they work together.",
   ["Describe circulatory, respiratory, and digestive systems", "Explain how body systems interact", "Connect nutrition to body function"], 4.0,
   prereqs=["science_g5_cells_organisms"])

_s("science", 6, "Earth Science", 4, "earth_history", "Earth's History",
   "Explore geologic time, fossils, and Earth's history.",
   ["Interpret the geologic time scale", "Explain how fossils form", "Describe major events in Earth's history"], 3.0)


_s("writing", 0, "Foundations", 1, "name_writing", "Writing My Name",
   "Practice writing first and last name with correct letter formation.",
   ["Write first name independently", "Form letters correctly", "Use appropriate spacing"], 2.0,
   activities=["lesson", "practice", "writing"])

_s("writing", 0, "Foundations", 2, "letter_writing", "Writing Letters",
   "Practice writing all uppercase and lowercase letters of the alphabet.",
   ["Write all uppercase letters", "Write all lowercase letters", "Copy simple words"], 4.0,
   prereqs=["writing_g0_name_writing"])

_s("writing", 0, "Composition", 3, "drawing_writing", "Drawing and Writing",
   "Use a combination of drawing and writing to share ideas and tell stories.",
   ["Draw pictures to express ideas", "Add labels to drawings", "Dictate or write simple sentences about drawings"], 3.0,
   prereqs=["writing_g0_letter_writing"])

_s("writing", 1, "Sentences", 1, "complete_sentences", "Writing Complete Sentences",
   "Write complete sentences with a subject and predicate, using capitalization and punctuation.",
   ["Write sentences with a capital letter and period", "Include a subject and verb", "Write questions with question marks"], 4.0,
   prereqs=["writing_g0_drawing_writing"])

_s("writing", 1, "Composition", 2, "personal_narrative_1", "Personal Narratives",
   "Write about personal experiences using a sequence of events.",
   ["Write about a real experience", "Include a beginning, middle, and end", "Add details about what happened and how you felt"], 4.0,
   prereqs=["writing_g1_complete_sentences"])

_s("writing", 1, "Mechanics", 3, "spelling_1", "Spelling Patterns",
   "Use common spelling patterns and phonics knowledge to spell words correctly.",
   ["Spell CVC words correctly", "Use common word families", "Apply phonics rules when spelling"], 3.0)

_s("writing", 2, "Paragraphs", 1, "paragraph_writing", "Writing Paragraphs",
   "Write organized paragraphs with a topic sentence, supporting details, and a closing sentence.",
   ["Write a clear topic sentence", "Add 3-4 supporting detail sentences", "Write a closing sentence"], 5.0,
   prereqs=["writing_g1_personal_narrative_1"])

_s("writing", 2, "Composition", 2, "opinion_writing_2", "Opinion Writing",
   "Write opinion pieces stating a topic, an opinion, and reasons that support the opinion.",
   ["State a clear opinion", "Give reasons to support the opinion", "Use linking words (because, also, and)"], 4.0,
   prereqs=["writing_g2_paragraph_writing"])

_s("writing", 2, "Mechanics", 3, "grammar_2", "Grammar and Punctuation",
   "Use correct grammar including nouns, verbs, adjectives, and proper punctuation.",
   ["Identify and use nouns, verbs, and adjectives", "Use commas in a series", "Use apostrophes for contractions and possessives"], 3.0)

_s("writing", 3, "Essays", 1, "essay_intro", "Introduction to Essays",
   "Write multi-paragraph essays with an introduction, body, and conclusion.",
   ["Write an engaging introduction", "Develop body paragraphs with evidence", "Write a concluding paragraph"], 6.0,
   prereqs=["writing_g2_paragraph_writing", "writing_g2_opinion_writing_2"])

_s("writing", 3, "Narrative", 2, "narrative_writing", "Narrative Writing",
   "Write narratives with developed characters, dialogue, and a clear sequence of events.",
   ["Create interesting characters", "Use dialogue effectively", "Organize events with transitions"], 5.0,
   prereqs=["writing_g3_essay_intro"])

_s("writing", 3, "Mechanics", 3, "revision", "Revising and Editing",
   "Revise writing for clarity and edit for grammar, spelling, and punctuation.",
   ["Reread writing for meaning", "Add, remove, or rearrange sentences", "Check spelling and punctuation"], 3.0)

_s("writing", 4, "Research", 1, "research_writing", "Research Writing",
   "Write research reports using information gathered from multiple sources.",
   ["Take notes from sources", "Organize information by subtopic", "Write a report with citations"], 6.0,
   prereqs=["writing_g3_essay_intro"])

_s("writing", 4, "Persuasive", 2, "persuasive_writing", "Persuasive Writing",
   "Write persuasive essays with a clear position supported by reasons and evidence.",
   ["State a clear claim", "Support with reasons and evidence", "Address counterarguments"], 5.0,
   prereqs=["writing_g3_essay_intro"])

_s("writing", 4, "Mechanics", 3, "grammar_adv", "Advanced Grammar",
   "Use complex sentences, proper verb tenses, and varied sentence structures.",
   ["Write compound and complex sentences", "Use consistent verb tenses", "Vary sentence beginnings and lengths"], 3.0)

_s("writing", 5, "Persuasive", 1, "argumentative", "Argumentative Writing",
   "Write argumentative essays that support claims with clear reasons and relevant evidence.",
   ["Develop a thesis statement", "Support arguments with evidence from multiple sources", "Use formal academic language"], 6.0,
   prereqs=["writing_g4_persuasive_writing"])

_s("writing", 5, "Informative", 2, "informative_writing", "Informative/Explanatory Writing",
   "Write informative texts that examine a topic and convey ideas clearly.",
   ["Introduce a topic clearly", "Develop the topic with facts and details", "Use precise language and domain-specific vocabulary"], 5.0,
   prereqs=["writing_g4_research_writing"])

_s("writing", 5, "Narrative", 3, "creative_writing", "Creative Writing",
   "Write creative narratives using literary techniques like foreshadowing and flashback.",
   ["Use descriptive sensory language", "Employ literary devices", "Develop a unique narrative voice"], 4.0)

_s("writing", 6, "Analytical", 1, "analytical_writing", "Analytical Writing",
   "Write analytical essays examining how authors use language and structure.",
   ["Analyze author's craft and style", "Cite textual evidence effectively", "Develop an analytical thesis"], 6.0,
   prereqs=["writing_g5_argumentative", "writing_g5_informative_writing"])

_s("writing", 6, "Research", 2, "extended_research", "Extended Research Projects",
   "Conduct sustained research projects synthesizing information from multiple sources.",
   ["Evaluate source credibility", "Synthesize information from multiple sources", "Follow a research methodology"], 6.0,
   prereqs=["writing_g4_research_writing"])

_s("writing", 6, "Digital", 3, "digital_writing", "Digital Communication",
   "Write for digital platforms including blogs, presentations, and multimedia projects.",
   ["Adapt writing for digital audiences", "Integrate text with visuals and media", "Practice digital citizenship in writing"], 3.0)


_s("social_studies", 0, "Community", 1, "self_family", "Me, My Family, My School",
   "Learn about self, family roles, and the school community.",
   ["Describe family members and roles", "Explain school rules and helpers", "Understand what makes a community"], 2.0,
   activities=["lesson", "practice", "video"])

_s("social_studies", 0, "Community", 2, "rules_safety", "Rules and Safety",
   "Understand why we have rules at home, school, and in the community.",
   ["Explain why rules are important", "Identify safety rules", "Practice following classroom rules"], 1.5)

_s("social_studies", 0, "Culture", 3, "holidays_traditions", "Holidays and Traditions",
   "Learn about different holidays and cultural traditions.",
   ["Name major holidays", "Describe family traditions", "Respect different cultural celebrations"], 2.0)

_s("social_studies", 1, "Geography", 1, "maps_intro", "Introduction to Maps",
   "Learn to read and use simple maps and globes.",
   ["Identify map features (title, key, compass rose)", "Locate places on a simple map", "Understand globe vs. flat map"], 3.0)

_s("social_studies", 1, "Community", 2, "neighborhoods", "Neighborhoods and Communities",
   "Explore different types of communities (urban, suburban, rural).",
   ["Describe urban, suburban, and rural communities", "Identify community helpers", "Compare different neighborhoods"], 2.5)

_s("social_studies", 1, "Economics", 3, "needs_wants", "Needs and Wants",
   "Distinguish between needs and wants and understand basic economics.",
   ["Identify basic needs vs. wants", "Understand goods and services", "Explain why people work"], 2.0)

_s("social_studies", 2, "Government", 1, "local_gov", "Local Government",
   "Learn about local government, leaders, and how decisions are made.",
   ["Identify local government leaders", "Explain how local laws are made", "Describe the role of citizens"], 3.0,
   prereqs=["social_studies_g0_rules_safety"])

_s("social_studies", 2, "Geography", 2, "landforms_water", "Landforms and Bodies of Water",
   "Identify and describe major landforms and bodies of water.",
   ["Name major landforms (mountains, plains, valleys)", "Identify bodies of water (oceans, rivers, lakes)", "Use maps to locate geographic features"], 2.5,
   prereqs=["social_studies_g1_maps_intro"])

_s("social_studies", 2, "History", 3, "past_present", "Past and Present",
   "Compare life in the past to life today and understand how things change over time.",
   ["Compare past and present tools and technology", "Identify how daily life has changed", "Understand timelines"], 2.5)

_s("social_studies", 3, "History", 1, "state_history", "Our State's History",
   "Learn about the history of your state including Native peoples, settlers, and key events.",
   ["Describe early inhabitants", "Explain key events in state history", "Identify important historical figures"], 4.0,
   prereqs=["social_studies_g2_past_present"])

_s("social_studies", 3, "Geography", 2, "regions", "Geographic Regions",
   "Explore geographic regions, natural resources, and how geography affects communities.",
   ["Identify geographic regions", "Describe how resources affect communities", "Explain human-environment interaction"], 3.0,
   prereqs=["social_studies_g2_landforms_water"])

_s("social_studies", 3, "Civics", 3, "rights_responsibilities", "Rights and Responsibilities",
   "Understand the rights and responsibilities of citizens in a democracy.",
   ["Identify basic rights (speech, voting, education)", "Describe citizen responsibilities", "Explain the importance of civic participation"], 2.5)

_s("social_studies", 4, "Geography", 1, "us_regions", "Regions of the United States",
   "Study the five regions of the United States and their characteristics.",
   ["Name and locate the five US regions", "Describe each region's geography and climate", "Compare resources and industries across regions"], 5.0,
   prereqs=["social_studies_g3_regions"])

_s("social_studies", 4, "History", 2, "early_america", "Early American History",
   "Learn about Native Americans, exploration, and the founding of the colonies.",
   ["Describe Native American cultures", "Explain European exploration and its impact", "Understand the founding of the 13 colonies"], 5.0,
   prereqs=["social_studies_g3_state_history"])

_s("social_studies", 4, "Economics", 3, "economics_basic", "Basic Economics",
   "Understand supply and demand, producers and consumers, and economic choices.",
   ["Explain supply and demand", "Describe producers and consumers", "Understand opportunity cost"], 3.0,
   prereqs=["social_studies_g1_needs_wants"])

_s("social_studies", 5, "History", 1, "us_history", "United States History",
   "Study major events in US history from the Revolution through the Civil War.",
   ["Describe causes and effects of the American Revolution", "Explain the Constitution and Bill of Rights", "Analyze the causes of the Civil War"], 8.0,
   prereqs=["social_studies_g4_early_america"])

_s("social_studies", 5, "Government", 2, "us_government", "US Government",
   "Understand the three branches of government and how they work together.",
   ["Describe the legislative, executive, and judicial branches", "Explain checks and balances", "Understand the election process"], 4.0,
   prereqs=["social_studies_g2_local_gov"])

_s("social_studies", 5, "Geography", 3, "western_hemisphere", "Western Hemisphere Geography",
   "Explore the geography, cultures, and economies of North and South America.",
   ["Locate countries in the Western Hemisphere", "Describe diverse cultures and languages", "Analyze how geography affects development"], 4.0,
   prereqs=["social_studies_g4_us_regions"])

_s("social_studies", 6, "History", 1, "world_cultures", "World Cultures and Civilizations",
   "Study ancient civilizations and their contributions to the modern world.",
   ["Describe major ancient civilizations (Mesopotamia, Egypt, Greece, Rome)", "Explain contributions to law, government, and culture", "Compare and contrast ancient societies"], 7.0,
   prereqs=["social_studies_g5_us_history"])

_s("social_studies", 6, "Geography", 2, "world_geography", "World Geography",
   "Study the Eastern Hemisphere including physical features, climate, and human geography.",
   ["Locate major countries and features on a world map", "Describe climate zones and biomes", "Analyze population distribution and urbanization"], 5.0,
   prereqs=["social_studies_g5_western_hemisphere"])

_s("social_studies", 6, "Civics", 3, "global_citizenship", "Global Citizenship",
   "Explore global issues, human rights, and the responsibilities of global citizens.",
   ["Describe the United Nations and its mission", "Discuss human rights and social justice", "Analyze global challenges (environment, poverty, conflict)"], 4.0)


async def seed_curriculum(db: AsyncSession):
    result = await db.execute(select(func.count()).select_from(CurriculumStandard))
    count = result.scalar()
    if count and count > 0:
        logger.info("Curriculum already seeded (%d standards)", count)
        return

    for item in CURRICULUM:
        standard = CurriculumStandard(**item)
        db.add(standard)

    await db.commit()
    logger.info("Seeded %d curriculum standards", len(CURRICULUM))
