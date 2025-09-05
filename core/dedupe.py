from __future__ import annotations
from typing import List, Tuple
from .doi import normalize_title


def build_index(entries: List[Tuple[str, str, dict]]) -> dict:
	"""Build an index to find duplicate bibliographic entries.

	Args:
		entries: A list of tuples of the form (key, bibtex_str, metadata_dict).
			- key: an identifier for the entry (ignored by this function).
			- bibtex_str: the raw bibtex string (ignored by this function).
			- metadata_dict: a dictionary expected to contain bibliographic
			  metadata under either top-level keys (e.g. "doi", "title", "year")
			  or nested under a "metadata" key.

	Returns:
		A dictionary with two keys:
		- "doi": maps normalized DOI (lowercased string) -> list of indices in
		  the input `entries` where that DOI occurs.
		- "title_year": maps (normalized_title, year) tuples -> list of indices
		  where that title/year occurs.

	Behavior and notes:
		- DOI lookup: the function attempts to read a DOI from
		  meta.get("metadata", {}).get("doi") or meta.get("doi"). If present,
		  the DOI is lowercased and used as the key.
		- Title normalization: titles are normalized via normalize_title(...)
		  to improve matching across minor differences (case, punctuation, etc).
		- Year lookup: reads meta.get("metadata", {}).get("year") or
		  meta.get("year"). Only entries with both a normalized title and a year
		  contribute to the "title_year" index.
		- Entries lacking DOI or title/year are omitted from the corresponding
		  index (they are not considered for duplicates by that method).
		- The function does not deduplicate entries itself; it only creates the
		  indices used for duplicate detection.

	Complexity:
		Time: O(n * T) where n is number of entries and T is cost of title
		normalization. Space: O(n) for index structures.

	Example:
		entries = [
			("k1", "@article{...}", {"doi": "10.1000/xyz", "title": "My Paper", "year": "2020"}),
			("k2", "@article{...}", {"metadata": {"doi": "10.1000/xyz"}}),
		]
		idx = build_index(entries)
		# idx["doi"]["10.1000/xyz"] -> [0, 1]
	"""
	idx = {"doi": {}, "title_year": {}}
	for i, (_, _, meta) in enumerate(entries):
		doi = (meta.get("metadata", {}).get("doi") or meta.get("doi") or "").lower()
		title = normalize_title(
			meta.get("metadata", {}).get("title") or meta.get("title") or ""
		)
		year = meta.get("metadata", {}).get("year") or meta.get("year") or ""
		if doi:
			idx["doi"].setdefault(doi, []).append(i)
		if title and year:
			idx["title_year"].setdefault((title, year), []).append(i)
	return idx


def find_duplicates(entries: List[Tuple[str, str, dict]]) -> List[int]:
	"""Identify duplicate entries and return indices to drop (keeping the first).

	Args:
		entries: A list of tuples (key, bibtex_str, metadata_dict) as accepted by
			build_index.

	Returns:
		A sorted list of integer indices into `entries` that should be dropped in
		order to remove duplicates. For any set of entries considered duplicates
		(by DOI or by title+year), the function keeps the first occurrence and
		returns the indices of subsequent occurrences.

	Behavior and precedence:
		- This function builds indices by DOI and by normalized (title, year).
		- For each group of entries sharing the same DOI or the same
		  (normalized_title, year), it marks all but the first index in that
		  group for dropping.
		- If an entry appears in multiple duplicate groups, it may be marked by
		  the first group processed; the final returned list is the union of
		  all such marks.
		- The returned list is sorted ascending so it can be applied safely when
		  removing items from the original list (remove higher indices first).

	Edge cases:
		- Entries without DOI and without a valid title+year will not be marked
		  as duplicates by this function.
		- The function is deterministic: it always keeps the lowest index
		  occurrence among duplicates.

	Example:
		# Given entries where indices 0 and 2 share the same DOI:
		duplicates = find_duplicates(entries)
		# duplicates might be [2] to drop the second occurrence.

	"""
	idx = build_index(entries)
	to_drop: set[int] = set()
	for mapping in (idx["doi"], idx["title_year"]):
		for _, indices in mapping.items():
			if len(indices) > 1:
				to_drop.update(indices[1:])
	return sorted(to_drop)
