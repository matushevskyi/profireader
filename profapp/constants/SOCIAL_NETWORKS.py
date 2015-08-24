SOCIAL_NETWORKS = [
    'profireader',
    'google',
    'facebook',
    'linkedin',
    'twitter',
    'microsoft',
    'yahoo',
]

SOC_NET_FIELDS = [
    'id',
    'email',
    'first_name',
    'last_name',
    'name',
    'gender',
    'link',
    'phone',
]

INFO_ITEMS_NONE = dict((field, None) for field in SOC_NET_FIELDS)

SOC_NET_NONE = dict((soc_net, INFO_ITEMS_NONE)
                    for soc_net in SOCIAL_NETWORKS)

for soc_net in SOCIAL_NETWORKS:
    SOC_NET_NONE[soc_net].update(dict([('phone', '')]))

SOCIAL_NETWORKS_SHORT = \
    [soc_net for soc_net in SOCIAL_NETWORKS if soc_net != 'profireader']

DB_FIELDS = dict((soc_net,
                 dict((field, (soc_net+'_'+field))
                      for field in SOC_NET_FIELDS))
                 for soc_net in SOCIAL_NETWORKS_SHORT)

SOC_NET_FIELDS_SHORT = [field for field in SOC_NET_FIELDS if field != 'id']

DB_FIELDS['profireader'] = dict((field, 'profireader'+'_'+field)
                                for field in SOC_NET_FIELDS_SHORT)

#DB_FIELDS['profireader'].update({'id': 'id'})
