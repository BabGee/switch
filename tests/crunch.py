import json
import logging as log

from administration.models import AccessLevel, Gateway, Channel
from upc.models import Institution
from bridge.models import Service
from iic.models import Page, \
    ServiceCommand, \
    PageInputGroup, \
    PageInput, \
    PageGroup, \
    InputVariable, \
    VariableType, \
    PageInputStatus

debug = True

if debug:
    log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
else:
    log.basicConfig(format="%(levelname)s: %(message)s")

# h1 = log.StreamHandler(sys.stdout)
# rootLogger = log.getLogger()
# rootLogger.addHandler(h1)

# doc
"""
+SERVICE
    +service_commands
        1 get_section
        3 get_interface
    +pages
        1 page 1    
            +page input groups
                +page inputs
                    TEXT VIEW
                    
+SERVICE2
    +service_commands
        1 get_section
        3 get_interface
    +pages
        1 page 1    
            +page input groups
                +page inputs
                    TEXT VIEW
                    
"""
# start level constants

SERVICES = 1
SERVICE_COMMANDS = 1.2
PAGE_GROUPS = 2
PAGES = 3
PAGE_INPUT_GROUPS = 3
PAGE_INPUTS = 5

start = PAGE_GROUPS

# example
config_heri_login_register = [  # list of services
    dict(
        name="SERVICE1",
        service_commands=[
            dict(
                name='get_section'
            )
        ],
        page_groups=[
            # dict(
            #     name='Login',
            #     item_level=-1,  # next item_level
            #     # description='',
            #     icon=None,
            #     gateways=['nikobizz'],
            #     pages=[
            #         dict(
            #             name='Login',
            #             description='Login',
            #             icon=None,
            #             item_level=-1,
            #             access_levels=['SYSTEM'],
            #             services=['INSTITUTION PAGE'],
            #             gateways=[],
            #             page_input_groups=[
            #                 dict(
            #                     name='Login',
            #                     description='Login',
            #                     icon=None,
            #                     item_level=-1,
            #                     input_variable=True,  # True is FORM, False is HIDDEN FORM
            #                     service='LOGIN',
            #                     section_size='24|24|24',
            #                     section_height=900,
            #                     gateways=[],
            #                     page_inputs=[
            #                         dict(
            #                             name='username',
            #                             variable_type='TEXT INPUT',
            #                             validate_min=0,
            #                             validate_max=0
            #
            #                         ),
            #                         dict(
            #                             name='password',
            #                             variable_type='PASSWORD INPUT',
            #                             validate_min=0,
            #                             validate_max=0
            #
            #                         ),
            #                         dict(
            #                             name='Login',
            #                             variable_type='SUBMIT',
            #                             validate_min=0,
            #                             validate_max=0
            #
            #                         )
            #                     ]
            #                 )
            #             ]
            #         )
            #     ]
            # ),
            dict(
                name='Register',
                item_level=-1,  # next item_level
                # description='',
                icon=None,
                gateways=['nikobizz'],
                pages=[
                    dict(
                        name='Register',
                        description='Register',
                        icon=None,
                        item_level=-1,
                        access_levels=['SYSTEM'],
                        services=['INSTITUTION PAGE'],
                        gateways=[],
                        page_input_groups=[
                            dict(
                                name='Register',
                                description='Register',
                                icon=None,
                                item_level=-1,
                                input_variable=True,  # True is FORM, False is HIDDEN FORM
                                service = 'REGISTER',
                                section_size='24|24|24',
                                section_height=900,
                                gateways=[],
                                page_inputs=[
                                    dict(
                                        name='first_name',
                                        variable_type='TEXT INPUT',
                                        validate_min=1,
                                        validate_max=30

                                    ),
                                    dict(
                                        name='last_name',
                                        variable_type='TEXT INPUT',
                                        validate_min=1,
                                        validate_max=30

                                    ),
                                    dict(
                                        name='email',
                                        variable_type='EMAIL INPUT',
                                        validate_min=5,
                                        validate_max=100

                                    ),
                                    dict(
                                        name='password',
                                        variable_type='PASSWORD INPUT',
                                        validate_min=8,
                                        validate_max=30

                                    ),
                                    dict(
                                        name='confirm_password',
                                        variable_type='PASSWORD INPUT',
                                        validate_min=8,
                                        validate_max=30

                                    ),
                                    dict(
                                        name='Register',
                                        variable_type='SUBMIT',
                                        validate_min=0,
                                        validate_max=0

                                    )
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )
]


def summary(dct, just_len):
    """

    :type dct: dict
    :param dct:
    :param just_len
    :return:
    """
    to_r = dict()
    keys = dct.keys()
    for k in keys:
        # ignore recursive dictionaries
        # if isinstance(dct.get(k), dict): continue
        if k == just_len:
            to_r[k] = len(dct.get(k))
        else:
            to_r[k] = dct.get(k)

    return json.dumps(to_r, indent=4, sort_keys=True)


def process_page_inputs(service, page_group, page, page_input_group, page_inputs):
    log.info(
        '[*] __________________________ processing [{}] page_inputs for page input group: {}'.format(
            len(page_inputs),
            page_input_group.name  # todo if None
        )
    )
    for page_input_config in page_inputs:
        log.info("\tProcessing Page Input")
        log.info(page_input_config)
        name = page_input_config.get('name')

        page_input = PageInput()
        page_input.page_input = name
        log.info("\t Page Input : {}".format(page_input.page_input))
        page_input.section_size = '24|24|24'
        log.info("\t Section Size : {}".format(page_input.section_size))
        level = page_input_config.get('item_level')
        if level < 0:
            level_page_inputs = page_input_group.pageinput_set.order_by('item_level')
            highest_page_input = level_page_inputs.last()
            if highest_page_input:
                if highest_page_input.item_level.isdigit():
                    page_input.item_level = int(highest_page_input.item_level) + 1
                else:
                    page_input.item_level = level_page_inputs.count() + 1
                    log.warn('[*] Level assigned using count')
            else:
                page_input.item_level = 0
        else:
            page_input.item_level = level
        log.info("\t Item Level: {}".format(page_input_group.item_level))

        log.info("\t Processing input variable")
        input_variable = InputVariable()
        input_variable.name = name

        # iic.models.VariableType
        input_variable.variable_type = VariableType.objects.get(name=page_input_config.get('variable_type'))

        input_variable.validate_min = page_input_config.get('validate_min', 0)
        input_variable.validate_max = page_input_config.get('validate_max', 0)
        # input_variable.default_value = None
        # input_variable.variable_kind = None
        input_variable.save()

        page_input.input_variable = input_variable  # iic.models.InputVariable
        page_input.page_input_group = page_input_group

        # todo import PageInputStatus model data
        page_input.page_input_status = PageInputStatus.objects.get_or_create(
            name='ACTIVE'
        )[0]  # iic.models.PageInputStatus
        page_input.page = page

        log.info("\t\t Save Page Input")
        page_input.save()
        log.info("\t\t Saved Page Input")

        # todo page_input.trigger = None  # bridge.models.Trigger
        page_input.access_level.add(*AccessLevel.objects.filter(name__in=page_input_config.get('access_levels', [])))
        log.info("\t\t Access Levels: {}".format(page_input.access_level_list()))

        page_input.gateway.add(*Gateway.objects.filter(name__in=page_input_config.get('gateways', [])))
        # administration.models.Gateway
        log.info("\t\t Gateways: {}".format(page_input.gateway_list()))

        # upc.models.Institution
        page_input.institution.add(*Institution.objects.filter(name__in=page_input_config.get('institutions', [])))
        log.info("\t\t Institutions: {}".format(page_input.institution_list()))

        # admin.Channel
        default_channels = {
            'iOS', 'BlackBerry', 'Amazon Kindle', 'Windows Phone'
        }
        passed_channels = page_input_config.get('channels', [])
        if len(passed_channels):
            for c in passed_channels:
                default_channels.add(c)
        else:
            default_channels.add('WEB')
            default_channels.add('Android')

        page_input.channel.add(*Channel.objects.filter(name__in=default_channels))
        # todo optimize with ids
        log.info("\t\t Channels: {}".format(page_input.channel_list()))

        log.info('[*] New .. {} -> {} -> {}'.format(
            page_input._meta.app_label,
            page_input._meta.object_name,
            page_input.id
        ))


def process_page_input_groups(service, page_group, page, page_input_groups):
    log.info(
        '[*] __________________________ processing [{}] page_input_groups for page group: {}, page: {}, service {}'.format(
            len(page_input_groups),
            page_group.name,  # todo what if None
            page.name,  # todo what if None
            service
        )
    )

    for page_input_group_config in page_input_groups:
        log.info("\tProcessing Page Input Group")
        log.info(summary(page_input_group_config, 'page_inputs'))
        name = page_input_group_config.get('name')

        page_input_group = PageInputGroup()
        page_input_group.name = name
        log.info("\t Name : {}".format(page_input_group.name))

        page_input_group.description = page_input_group_config.get('description', name)
        log.info("\t Description: {}".format(page_input_group.description))

        level = page_input_group_config.get('item_level', -1)
        if level < 0:
            level_page_input_group = PageInputGroup.objects.order_by('item_level')
            highest_page_input_group = level_page_input_group.last()
            if highest_page_input_group:
                if highest_page_input_group.item_level.isdigit():
                    page_input_group.item_level = int(highest_page_input_group.item_level) + 1
                else:
                    page_input_group.item_level = level_page_input_group.count() + 1
                    log.warn('[*] Level assigned using count')
            else:
                page_input_group.item_level = 0
        else:
            page_input_group.item_level = level
        log.info("\t Item Level: {}".format(page_input_group.item_level))

        input_variable = InputVariable()
        # input_variable.name = name

        input_variable.variable_type = VariableType.objects.get(name='FORM')  # iic.models.VariableType
        # todo assigning variable_type using id is better
        # todo FORM & HIDDEN FORM

        input_variable.validate_min = 0
        input_variable.validate_max = 0
        # input_variable.variable_kind = None
        # todo create submit service and service commands
        # input_variable.default_value = page_input_group_config.get('service')
        input_variable.name = page_input_group_config.get('service')

        
        input_variable.save()

        page_input_group.input_variable = input_variable  # iic.models.InputVariable
        page_input_group.section_size = '24|24|24'
        page_input_group.section_height = 900

        page_input_group.save()

        # administration.models.Gateway
        page_input_group.gateway.add(*Gateway.objects.filter(name__in=page_input_group_config.get('gateways', [])))

        log.info('[*] New .. {} -> {} -> {}'.format(
            page_input_group._meta.app_label,
            page_input_group._meta.object_name,
            page_input_group.id
        ))

        process_page_inputs(service, page_group, page, page_input_group, page_input_group_config.get('page_inputs'))


def process_pages(service, page_group, pages):
    log.info('[*] _______________________ processing [{}] pages for page_group: {}, service {}'.format(
        len(pages),
        page_group.name,  # todo what if None
        service
    )
    )
    for page_config in pages:
        log.info("\tProcessing Page")
        log.info(summary(page_config, 'page_input_groups'))
        page = Page()

        page.name = page_config.get('name')
        log.info("\t Name : {}".format(page.name))

        page.description = page_config.get('description', page.name)
        log.info("\t Description: {}".format(page.description))


        services = page_config.get('services',[])

        level = page_config.get('item_level')
        if level < 0:
            if len(services):
                level_pages = Page.objects.filter(service__name__in=services).order_by('item_level')
            else:
                # todo this should not happen
                level_pages = page_group.page_set.order_by('item_level')

            highest_page = level_pages.last()
            if highest_page:
                if str(highest_page.item_level).isdigit():
                    page.item_level = int(highest_page.item_level) + 1
                else:
                    page.item_level = level_pages.count() + 1
                    log.warn('[*] Level assigned using count')

            else:
                page.item_level = 0
        else:
            page.item_level = level
        log.info("\t Item Level: {}".format(page.item_level))

        page.page_group = page_group  # iic.models.PageGroup
        log.info("\t Page Group: {}".format(page.page_group))

        log.info("\t Save Page")
        page.save()
        log.info("\t Saved Page")

        page.access_level.add(*[al for al in AccessLevel.objects.filter(name__in=page_config.get('access_levels', []))])
        log.info("\t Access Levels: {}".format(page.access_level_list()))

        page.gateway.add(*Gateway.objects.filter(name__in=page_config.get('gateways')))  # administration.models.Gateway
        log.info("\t Gateways: {}".format(page.gateway_list()))

        # todo set to current service if list is empty
        page.service.add(*Service.objects.filter(name__in=services))  # bridge.models.Service
        log.info("\t Services: {}".format(page.service_list()))

        log.info('[*] New .. {} -> {} -> {}'.format(
            page._meta.app_label,
            page._meta.object_name,
            page.id
        ))
        process_page_input_groups(service, page_group, page, page_config.get('page_input_groups'))


def process_page_groups(service, page_groups):
    log.info('[*] __________________________ processing [{}] page_groups, service {}'.format(len(page_groups), service))
    for page_group_config in page_groups:
        log.info("Processing Page Group")
        log.info(summary(page_group_config, 'pages'))

        name = page_group_config.get('name')
        try:
            page_group = PageGroup.objects.get(name=name)
            log.warn('page group {} already existed.'.format(page_group.name))
            # todo make conditional
            # now if page_group use it, don't create new

            log.info('[*] Using .. {} -> {} -> {}'.format(
                page_group._meta.app_label,
                page_group._meta.object_name,
                page_group.id
            ))
            process_pages(service, page_group, page_group_config.get('pages'))
            return
        except PageGroup.DoesNotExist:
            page_group = PageGroup(name=name)

        log.info("\t Name : {}".format(page_group.name))
        page_group.description = page_group_config.get('description', name)
        log.info("\t Description: {}".format(page_group.description))

        level = page_group_config.get('item_level')
        if level < 0:
            gateways = page_group_config.get('gateways', [])
            if len(gateways):
                level_page_groups = PageGroup.objects \
                    .filter(gateway__name__in=gateways) \
                    .order_by('item_level')
            else:
                level_page_groups = PageGroup.objects \
                    .filter() \
                    .order_by('item_level')

            highest_page_group = level_page_groups.last()
            if highest_page_group:
                # todo are item-levels here always integers?
                if str(highest_page_group.item_level).isdigit():
                    page_group.item_level = int(highest_page_group.item_level) + 1
                else:
                    page_group.item_level = level_page_groups.count() + 1
                    log.warn('[*] Level assigned using count')

            else:
                page_group.item_level = 0
        else:
            page_group.item_level = level
        log.info("\t Item Level: {}".format(page_group.item_level))

        log.info("\t Save Page Group")
        page_group.save()
        log.info("\t Saved Page Group, {}".format(page_group))

        # administration.models.Gateway
        page_group.gateway.add(*Gateway.objects.filter(name__in=page_group_config.get('gateways')))
        log.info("\t Gateways: {}".format(page_group.gateway_list()))

        log.info('[*] New .. {} -> {} -> {}'.format(
            page_group._meta.app_label,
            page_group._meta.object_name,
            page_group.id
        ))
        process_pages(service, page_group, page_group_config.get('pages'))


def process_service_commands(service, service_commands):
    for service_command_config in service_commands:
        service_command = ServiceCommand()

        service_command.command_function = None
        service_command.level = 0  # TODO
        service_command.service = service
        service_command.node_system = None  # api.models.NodeSystem
        service_command.status = None
        service_command.description = None
        service_command.access_level = None  # administration.models.AccessLevel
        service_command.channel = None  # administration.models.Channel
        service_command.trigger = None  # bridge.models.Trigger
        service_command.gateway = None  # administration.models.Gateway

        service_command.save()


def process_services(config):
    for service_config in config:
        name = service_config.get('name')
        service = Service.objects.get(name=name)
        service.name = None
        service.description = None
        service.product = None
        service.access_level = None
        service.status = None  # fk ServiceStatus
        service.save()

        process_service_commands(service, service_config.get('service_commands', []))
        process_page_groups(service, service_config.get('pages', []))


def run(configs, start_level=1):
    """

    :type configs:dict
    :param configs: switch/service configurations
    :param start_level: the starting point of creating interface
    :return:
    """
    if start_level == 1:
        process_services(configs)
    elif start_level == 2:
        process_page_groups(None, configs[0]['page_groups'])


# test run
run(config_heri_login_register, start)
