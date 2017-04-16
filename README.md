# French_Deputies_db :globe_with_meridians:

This python script aim at extracting informations about french deputies from this website [French National Assembly](http://www2.assemblee-nationale.fr).

This script was made to be used by association but everyone is pleased to use this script. I am in no way responsible of how the informations collected are used.

The last extracted db is available as `deputies.csv`. (last extraction : 16 april 2017)

FYI the columns are
```python
[
    'name', 'email', 'phone',
    'date_of_birth', 'place_of_birth',
    'circonscription', 'state',
    'group', 'group_url',
    'commission', 'commission_url',
    'substitute', 'fundings',
    'decl_interet_activite_url', 'address'
]
```

## Requirement
python, beautifulsoup4
