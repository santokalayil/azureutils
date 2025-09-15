# Recursive chunking for markdown with page and section mapping
import re
from typing import List, Dict, Any
def dummy_tokenizer(text: str) -> int:
	"""Dummy tokenizer: returns number of words as token count."""
	return len(text.split())
def get_page_ranges(page_map: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
	"""Returns list of page ranges with start/end indices and page number."""
	pages = []
	for entry in page_map:
		# Extract page number from comment_tag_text
		m = re.search(r'Page (\d+) of (\d+)', entry['comment_tag_text'])
		page_num = int(m.group(1)) if m else None
		pages.append({
			'page_num': page_num,
			'start_idx': entry['start_idx'],
			'end_idx': entry['end_idx']
		})
	return pages

def get_sections(markdown: str) -> List[Dict[str, Any]]:
	"""Parse markdown for sections/subsections by hash count."""
	section_pattern = re.compile(r'^(#{1,6})\s+(.*)', re.MULTILINE)
	sections = []
	for m in section_pattern.finditer(markdown):
		level = len(m.group(1))
		heading = m.group(2).strip()
		start_idx = m.start()
		sections.append({
			'level': level,
			'heading': heading,
			'start_idx': start_idx
		})
	# Add end_idx for each section
	for i in range(len(sections)):
		if i < len(sections) - 1:
			sections[i]['end_idx'] = sections[i+1]['start_idx']
		else:
			sections[i]['end_idx'] = len(markdown)
	return sections

def find_page_for_index(pages: List[Dict[str, Any]], idx: int) -> int:
	"""Find page number for a given index."""
	for page in pages:
		if idx >= page['start_idx'] and idx < page['end_idx']:
			return page['page_num']
	return None

def recursive_chunk(text: str, meta: Dict[str, Any], n_tokens: int) -> List[Dict[str, Any]]:
	"""Recursively chunk text into n_tokens size, preserving metadata."""
	tokens = text.split()
	chunks = []
	for i in range(0, len(tokens), n_tokens):
		chunk_text = ' '.join(tokens[i:i+n_tokens])
		chunk_meta = meta.copy()
	chunk_meta['chunk_start_token'] = i
	chunk_meta['chunk_end_token'] = i + len(chunk_text.split())
	chunks.append({
			'content': chunk_text,
			'meta': chunk_meta
		})
	return chunks

def chunk_markdown(markdown: str, page_map: List[Dict[str, Any]], n_tokens: int = 50) -> List[Dict[str, Any]]:
	pages = get_page_ranges(page_map)
	sections = get_sections(markdown)
	all_chunks = []
	for section in sections:
		section_text = markdown[section['start_idx']:section['end_idx']]
		page_num = find_page_for_index(pages, section['start_idx'])
		meta = {
			'section_heading': section['heading'],
			'section_level': section['level'],
			'page_num': page_num,
			'section_start_idx': section['start_idx'],
			'section_end_idx': section['end_idx']
		}
		section_chunks = recursive_chunk(section_text, meta, n_tokens)
		all_chunks.extend(section_chunks)
	return all_chunks

# Dummy inputs for demonstration
dummy_markdown = """
# Heading 1
Some text for heading 1. More text here.
## Subheading 1.1
Text for subheading 1.1. Even more text here.
### SubSubheading 1.1.1
Text for subsubheading 1.1.1. Lorem ipsum dolor sit amet.
# Heading 2
Text for heading 2. More content here.
"""

dummy_page_map = [
	{
	"comment_tag_text": "<!-- PageNumber=\"Page 1 of 40\" -->",
	"start_idx": 0,
	"end_idx": 34
	},
	{
		"comment_tag_text": "<!-- PageNumber=\"Page 2 of 40\" -->",
		"start_idx": 100,
		"end_idx": 134
	}
]

if __name__ == "__main__":
	chunks = chunk_markdown(dummy_markdown, dummy_page_map, n_tokens=10)
	for i, chunk in enumerate(chunks):
		print(f"Chunk {i+1}: {chunk['meta']}")
		print(chunk['content'])
	print("-"*40)
