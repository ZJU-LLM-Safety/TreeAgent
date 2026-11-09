"""Bounded corrections to packaged sample wording and scoring contracts.

Contexts, answers and executable gold specifications are preserved. UIDs identify
source examples; sample_revision and manifest line hashes identify this revision.
"""
from __future__ import annotations

REVISION = 'sample_contract_v2'
QUESTION_UPDATES = {
    'json_subset_train_32k_numeric_extreme_000000': (
        'What is the cheapest base price available?',
        'Across all supplied car-rental records, what is the lowest listed rental price in USD? '
        'Return only the numerical value; do not convert currencies.'),
    'json_subset_dev_32k_numeric_extreme_000000': (
        'What is the cheapest base price available?',
        'Across all supplied car-rental records, what is the lowest listed rental price in USD? '
        'Return only the numerical value; do not convert currencies.'),
    'json_subset_dev_32k_record_multi_field_4_000000': (
        'For car 372903916, return the drive-away price, cleanliness rating, base price, deposit.',
        'For car 372903916, return its drive-away price in USD, cleanliness rating, '
        'listed rental price in USD, and base-currency deposit in INR, in that order. '
        'Give one value per line without labels or explanations; do not convert currencies.'),
    'html_websrc_v4_test_8k_conditional_count_00002': (
        'Across all semantic HTML records in the corpus, how many records have Release year equal to (2019)?',
        'Across the movie records in the supplied HTML documents, how many have a displayed '
        'Release year equal to "(2019)"? Count each movie record separately.'),
    'html_websrc_v4_test_8k_groupby_topk_values_00000': (
        'Across all semantic HTML records in the corpus, which three Destination values occur most often?',
        'Across the vehicle columns in the supplied HTML comparison tables, which three distinct '
        'Destination values occur most frequently? Count each vehicle column separately.'),
    'html_websrc_v4_test_8k_numeric_extreme_00000': (
        'Across all semantic HTML records in the corpus, what is the min Destination value?',
        'Across the vehicle columns in the supplied HTML comparison tables, what is the smallest '
        'numeric amount shown in the Destination field?'),
}
EXACT_NUMBER_UID = 'jss_2aac94a0d72f00388c30'
ORDERED_TASKS = {'multi_record_field_2', 'multi_record_field_4',
                 'record_multi_field_2', 'record_multi_field_4'}


def revise_sample(row: dict) -> dict:
    """Apply only the identified revisions, idempotently; reject unexpected wording."""
    row = dict(row)
    uid = row.get('uid', '')
    changed = False
    if uid in QUESTION_UPDATES:
        old, new = QUESTION_UPDATES[uid]
        if row['question'] not in (old, new):
            raise ValueError(f'{uid}: unexpected question for sample revision')
        row['question'] = new
        changed = True
    if uid == EXACT_NUMBER_UID:
        row['metric_type'] = 'exact_number_match'
        changed = True
    if uid.startswith('yaml_synthetic_fixture_'):
        task = row['task_subtype']
        if task in ORDERED_TASKS:
            row['answer_format'] = 'ordered_newline_values'
            row['answer_format_instruction'] = ('Give one value per line, in the order requested, '
                                                 'without labels or explanations.')
            row['metric_type'] = 'ordered_list_str_match'
        elif task == 'groupby_topk_values':
            row['answer_format_instruction'] = 'Return one value per line without counts or explanations.'
            row['metric_type'] = 'unordered_list_str_match'
        elif task in {'conditional_count', 'numeric_extreme'}:
            row['answer_format_instruction'] = 'Return only the numerical value.'
            row['metric_type'] = 'approx_number_match'
        else:
            row['answer_format_instruction'] = 'Return only the value.'
            row['metric_type'] = 'accuracy_string'
        changed = True
    if changed:
        row['sample_revision'] = REVISION
    return row
