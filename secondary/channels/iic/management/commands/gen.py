from django.core.management.base import BaseCommand, CommandError

import json

from primary.core.administration.models import \
    AccessLevel, \
    Gateway, \
    Channel
from primary.core.upc.models import \
    Institution
from primary.core.bridge.models import \
    Service, \
    ServiceStatus,\
    ServiceCommand,\
    Product
from secondary.channels.iic.models import \
    Page, \
    ServiceCommand, \
    PageInputGroup, \
    PageInput, \
    PageGroup, \
    InputVariable, \
    VariableType, \
    PageInputStatus

import logging as log
import os


class Utils:
    def __init__(self):
        pass

    @staticmethod
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


class IicGenerator:
    # start level constants

    SERVICES = 1
    SERVICE_COMMANDS = 1.2
    PAGE_GROUPS = 2
    PAGES = 3
    PAGE_INPUT_GROUPS = 3
    PAGE_INPUTS = 5

    # model actions
    DO_NOTHING = 0  # skip
    CREATE = 1  # create new, override pk if set, default
    EDIT = 2  # update properties, obj must have pk property,
    DELETE = 3 # delete

    def __init__(self, command, configs, start_level=2, db_save=False):
        """

        :type configs:dict
        :param configs: switch/service configurations
        :param start_level: the starting point of creating interface
        :return:
        """
        self.debug = True
        self.DB_SAVE = db_save
        self.verbosity = 0  # Simple Creation Process
        self.indent_level = 1
        self.start = IicGenerator.PAGE_GROUPS
        self.command = command

        self.update = False

        if self.debug:
            log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        else:
            log.basicConfig(format="%(levelname)s: %(message)s")

        self._start_level = start_level
        self._configs = configs

    def gen(self):

        if self._start_level == 1:
            self.process_services(self._configs)
        elif self._start_level == 2:
            self.process_page_groups(None, self._configs[0]['page_groups'])

    def process_page_inputs(self, service, page_group, page, page_input_group, page_inputs):
        indent = self.get_indent()
        self.set_indent(3)
        self.log(self.command.style.SUCCESS('[{}] Page Inputs'.format(len(page_inputs))), n=True)
        self.set_indent(4)

        for page_input_config in page_inputs:
            self.log('_' * 144, n=True)
            if self.verbosity: log.info(page_input_config)

            is_shared = page_input_config.get('from_shared', -1)
            if is_shared >= 0:
                page_input_config = self._configs[0]['global_configs']['page_inputs'][int(is_shared)]
                self.log("Name:{}".format(page_input_config.get('name')),n=True)
                self.log('shared {}'.format(is_shared))
                pk = page_input_config.get('input_variable', None)
                if pk:
                    self.log('existing')
                    try:
                        input_variable = InputVariable.objects.get(pk=pk)
                        self.log('{}'.format(input_variable.id))

                    except InputVariable.DoesNotExist:
                        pass
                else:
                    self.log('created')
                    input_variable = InputVariable()
                    input_variable.name = page_input_config.get('name')

                    # iic.models.VariableType
                    try:
                        input_variable.variable_type = VariableType.objects.get(
                            name=page_input_config.get('variable_type'))
                    except VariableType.DoesNotExist:
                        self.log(self.command.style.ERROR('NO ELEMENT'))
                        continue

                    input_variable.validate_min = page_input_config.get('validate_min', 0)
                    input_variable.validate_max = page_input_config.get('validate_max', 0)
                    input_variable.default_value = page_input_config.get('default_value', 0)
                    # input_variable.variable_kind = None

                    if self.DB_SAVE:
                        input_variable.save()
                        page_input_config['input_variable'] = input_variable.pk
                        self.log(self.command.style.SUCCESS('{}'.format(input_variable.pk)))
                    else:
                        pass

            else:
                input_variable = InputVariable()
                input_variable.name = page_input_config.get('name')
                self.log("Name:{}".format(page_input_config.get('name')), n=True)
                # iic.models.VariableType
                try:
                    input_variable.variable_type = VariableType.objects.get(name=page_input_config.get('variable_type'))
                except VariableType.DoesNotExist:
                    self.log(self.command.style.ERROR('NO ELEMENT'))
                    continue

                input_variable.validate_min = page_input_config.get('validate_min', 0)
                input_variable.validate_max = page_input_config.get('validate_max', 0)
                input_variable.default_value = page_input_config.get('default_value', 0)
                # input_variable.variable_kind = None

                if self.DB_SAVE:
                    input_variable.save()
                    page_input_config['input_variable'] = input_variable.pk
                    self.log(self.command.style.SUCCESS('created -> {}'.format(input_variable.pk)))
                else:
                    if self.verbosity:
                        log.info("should save input_variable {} but did not. DB_SAVE".format(input_variable))

            name = page_input_config.get('name')
            pk = page_input_config.get('pk', None)
            if pk:
                self.log('existing')
                try:
                    page_input = PageInput.objects.get(pk=pk)
                    self.log('{}'.format(page_group.id))
                    if not self.update:
                        continue

                except PageInput.DoesNotExist:
                    pass
            else:
                self.log('new')
                page_input = PageInput()

            # convert brian_nyaundi into Brian Nyaundi
            page_input.page_input = name.replace('_',' ').title()

            page_input.section_size = '24|24|24'

            self.log("Widths:{}".format(page_input.section_size))
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
            self.log("Level:{}".format(page_input_group.item_level))

            if self.verbosity: log.info(" Processing input variable")

            page_input.input_variable = input_variable  # iic.models.InputVariable

            # self.log(input_variable.name)
            self.log(input_variable.variable_type)

            page_input.page_input_group = page_input_group

            # todo import PageInputStatus model data
            # get will always succeed
            page_input.page_input_status = PageInputStatus.objects.get_or_create(
                name='ACTIVE'
            )[0]  # iic.models.PageInputStatus
            page_input.page = page

            if self.verbosity: log.info("\t\t Save Page Input")
            if self.DB_SAVE:
                page_input.save()
                self.log('saved -> {}'.format(page_input.pk))
                if self.verbosity: log.info("\t\t Saved Page Input")
            else:
                if self.verbosity: log.info("should save page_input {} but did not. DB_SAVE".format(page_input))

            # todo page_input.trigger = None  # bridge.models.Trigger
            if self.DB_SAVE:
                page_input.access_level.add(
                    *AccessLevel.objects.filter(name__in=page_input_config.get('access_levels', [])))
                if self.verbosity: log.info("\t\t Access Levels: {}".format(page_input.access_level_list()))
            else:
                if self.verbosity: log.info("should save page_input  Access Levels but did not. DB_SAVE")

            # administration.models.Gateway
            if self.DB_SAVE:
                page_input.gateway.add(*Gateway.objects.filter(name__in=page_input_config.get('gateways', [])))
                if self.verbosity: log.info("\t\t Gateways: {}".format(page_input.gateway_list()))
            else:
                if self.verbosity: log.info("should save page_input Gateways but did not. DB_SAVE")

            # upc.models.Institution
            if self.DB_SAVE:
                page_input.institution.add(
                    *Institution.objects.filter(name__in=page_input_config.get('institutions', [])))
                if self.verbosity: log.info("\t\t Institutions: {}".format(page_input.institution_list()))
            else:
                if self.verbosity: log.info("should save page_input Institutions but did not. DB_SAVE")

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

            # todo optimize with ids
            if self.DB_SAVE:
                page_input.channel.add(*Channel.objects.filter(name__in=default_channels))
                if self.verbosity: log.info("\t\t Channels: {}".format(page_input.channel_list()))
            else:
                if self.verbosity: log.info("should save page_input Channels but did not. DB_SAVE")

            if self.verbosity: log.info('[*] New .. {} -> {} -> {}'.format(
                page_input._meta.app_label,
                page_input._meta.object_name,
                page_input.id
            ))

    def process_page_input_groups(self, service, page_group, page, page_input_groups):
        indent = self.get_indent()
        self.set_indent(2)
        pigs_count = len(page_input_groups)
        self.log(self.command.style.SUCCESS('[{}] Page Input Groups'.format(pigs_count)), n=True)
        self.set_indent(3)

        if self.verbosity: log.info(
            '[*] __________________________ processing [{}] page_input_groups for page group: {}, page: {}, service {}'.format(
                len(page_input_groups),
                page_group.name,  # todo what if None
                page.name,  # todo what if None
                service
            )
        )

        for page_input_group_config in page_input_groups:
            self.log(self.command.style.SUCCESS('_' * 146), n=True)
            if self.verbosity: log.info(Utils.summary(page_input_group_config, 'page_inputs'))
            name = page_input_group_config.get('name')
            if not name and pigs_count == 1:
                name = page.name

            self.log("Name : {}".format(name), n=True)

            pk = page_input_group_config.get('pk', None)
            if pk:
                self.log('existing')
                try:
                    page_input_group = PageInputGroup.objects.get(pk=pk)

                    self.log('{}'.format(page_group.id))
                    if not self.update:
                        self.process_page_inputs(service, page_group, page, page_input_group,
                                                 page_input_group_config.get('page_inputs'))
                        continue
                except PageInputGroup.DoesNotExist:
                    pass
            else:
                self.log('new')
                page_input_group = PageInputGroup()

            page_input_group.name = name
            page_input_group.description = name

            page_input_group.description = page_input_group_config.get('description', name)
            self.log(" Description: {}".format(page_input_group.description))

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
            self.log(" Item Level: {}".format(page_input_group.item_level))

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

            # todo create configured service and commands

            service_name = page_input_group_config.get('service')
            if service_name:
                pass
            else:
                service_name = name.upper()

            self.log(service_name)
            input_variable.name = service_name
            # try:
            #     service = Service.objects.get(name=service_name)
            # except Service.DoesNotExist:
            #     service = Service(name=service_name)
            #
            #     service.description = service_name.title()
            #     service.product = Product.objects.get(name='SYSTEM')
            #     service.status = ServiceStatus.objects.get(name='POLLER')
            #     if self.DB_SAVE:
            #         service.save()
            #     else:
            #         if self.verbosity: self.info('service {} not saved'.format(service))
            #     service.access_level = None

            if self.DB_SAVE:
                input_variable.save()
            else:
                if self.verbosity: log.info(
                    "should save page_input_group input_variable {} but did not. DB_SAVE".format(input_variable.name))

            page_input_group.input_variable = input_variable  # iic.models.InputVariable
            page_input_group.section_size = '24|24|24'
            page_input_group.section_height = 900

            if self.DB_SAVE:
                page_input_group.save()
            else:
                if self.verbosity: log.info(
                    "should save page_input_group {} but did not. DB_SAVE".format(page_input_group))

            # administration.models.Gateway
            if self.DB_SAVE:
                page_input_group.gateway.add(
                    *Gateway.objects.filter(name__in=page_input_group_config.get('gateways', [])))
            else:
                if self.verbosity: log.info("should save page_input_group gateways but did not. DB_SAVE")

                if self.verbosity: log.info('[*] New .. {} -> {} -> {}'.format(
                    page_input_group._meta.app_label,
                    page_input_group._meta.object_name,
                    page_input_group.id
                ))

            self.process_page_inputs(service, page_group, page, page_input_group,
                                     page_input_group_config.get('page_inputs'))
        self.set_indent(indent)

    def process_pages(self, service, page_group, pages):
        indent = self.get_indent()
        self.set_indent(1)
        self.log(self.command.style.SUCCESS('[{}] Pages'.format(len(pages))), n=True)
        self.set_indent(2)
        for page_config in pages:
            self.log(self.command.style.WARNING('_' * 148), n=True)
            if self.verbosity: self.info(Utils.summary(page_config, 'page_input_groups'))

            name = page_config.get('name')

            self.log("Name : {}".format(name), n=True)
            pk = page_config.get('pk', None)
            if pk:
                self.log('existing')
                try:
                    page = Page.objects.get(pk=pk)
                    self.log(page.pk)

                    if not self.update:
                        self.process_page_input_groups(service, page_group, page, page_config.get('page_input_groups'))
                        continue

                except Page.DoesNotExist:
                    pass
            else:
                self.log('new')
                page = Page()

            page.name = name

            page.description = page_config.get('description', page.name)
            self.log(" Description: {}".format(page.description))

            services = page_config.get('services', [])

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
            self.log(" Item Level: {}".format(page.item_level))

            page.page_group = page_group  # iic.models.PageGroup
            self.log(" Page Group: {}".format(page.page_group))

            if self.verbosity: self.log(" Save Page")
            if self.DB_SAVE:
                page.save()
                self.log(page.pk)
                page_config['pk'] = page.pk
                if self.verbosity: self.info("\t Saved Page")
            else:
                if self.verbosity: self.info('should save page {}, but not saved, DB_SAVE'.format(page.name))

            if self.DB_SAVE:
                page.access_level.add(
                    *[al for al in AccessLevel.objects.filter(name__in=page_config.get('access_levels', []))])
                if self.verbosity: self.info("\t Access Levels: {}".format(page.access_level_list()))
            else:
                if self.verbosity: self.info("should save page access_levels but did not. DB_SAVE")

            if self.DB_SAVE:
                page.gateway.add(
                    *Gateway.objects.filter(name__in=page_config.get('gateways')))  # administration.models.Gateway
                if self.verbosity: self.info("\t Gateways: {}".format(page.gateway_list()))
            else:
                if self.verbosity: self.info("should save page gateways but did not. DB_SAVE")

            # todo set to current service if list is empty
            if self.DB_SAVE:
                page.service.add(*Service.objects.filter(name__in=services))  # bridge.models.Service
                if self.verbosity: self.info("\t Services: {}".format(page.service_list()))
            else:
                if self.verbosity: self.info("should save page services but did not. DB_SAVE")

            if self.verbosity: self.info('[*] New .. {} -> {} -> {}'.format(
                page._meta.app_label,
                page._meta.object_name,
                page.id
            ))
            self.process_page_input_groups(service, page_group, page, page_config.get('page_input_groups'))
        self.set_indent(indent)

    def process_page_groups(self, service, page_groups):
        indent = self.get_indent()
        self.set_indent(0)
        self.log(self.command.style.SUCCESS('[{}] Page Groups'.format(len(page_groups))))
        self.set_indent(1)

        for page_group_config in page_groups:
            self.log(self.command.style.ERROR('_' * 150), n=True)
            if self.verbosity: self.info(Utils.summary(page_group_config, 'pages'))

            name = page_group_config.get('name')
            self.log(name, n=True)

            if page_group_config.get('pk') != 4:
                self.log('skip not 4')
                continue

            try:
                page_group = PageGroup.objects.get(name=name)
                if self.verbosity: log.warn('page group {} already existed.'.format(page_group.name))
                self.log('existing*')
                # todo make conditional
                # now if page_group use it, don't create new

                self.log('{}'.format(page_group.id))

                if not self.update:
                    self.process_pages(service, page_group, page_group_config.get('pages'))
                    continue

            except PageGroup.DoesNotExist:
                page_group = PageGroup(name=name)
                self.log('new*')

            # self.info("\t Name : {}".format(page_group.name))
            page_group.description = page_group_config.get('description', name)
            # self.info("\t Description: {}".format(page_group.description))

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
            if self.verbosity:self.info("\t Item Level: {}".format(page_group.item_level))

            if self.verbosity:self.info("\t Save Page Group")
            if self.DB_SAVE:
                page_group.save()
                page_group_config['pk'] = page_group.pk
                self.log(self.command.style.SUCCESS('saved -> {}'.format(page_group.pk)))
                if self.verbosity: self.info("\t Saved Page Group, {}".format(page_group))
            else:
                if self.verbosity:self.info('should save page_group {}, but not saved, DB_SAVE'.format(page_group))


            # administration.models.Gateway
            if self.DB_SAVE:
                page_group.gateway.add(*Gateway.objects.filter(name__in=page_group_config.get('gateways')))
                if self.verbosity:self.info("\t Gateways: {}".format(page_group.gateway_list()))
            else:
                if self.verbosity:self.info("should add page_group gateways but did not. DB_SAVE")

            if self.verbosity:self.info('[*] New .. {} -> {} -> {}'.format(
                page_group._meta.app_label,
                page_group._meta.object_name,
                page_group.id
            ))
            self.process_pages(service, page_group, page_group_config.get('pages'))

        self.set_indent(indent)

    def process_service_commands(self, service, service_commands):
        for service_command_config in service_commands:

            service_command = ServiceCommand()

            service_command.command_function = service_command_config.get('name')
            service_command.level = 0  # TODO
            service_command.service = service
            service_command.node_system = None  # api.models.NodeSystem
            service_command.status = None
            service_command.description = None

            if self.DB_SAVE:
                service_command.save()
            else:
                self.info('service_command {} not saved, DB_SAVE = {}'.format(service_command, self.DB_SAVE))

            service_command.access_level = None  # administration.models.AccessLevel
            service_command.channel = None  # administration.models.Channel
            service_command.trigger = None  # bridge.models.Trigger
            service_command.gateway = None  # administration.models.Gateway

    def process_services(self, config):
        for service_config in config:
            name = service_config.get('name')
            try:
                service = Service.objects.get(name=name)
            except Service.DoesNotExist:
                service = Service(name=name)

                service.description = name
                service.product = Product.objects.get(name='SYSTEM')

                service.status = ServiceStatus.objects.get(name='POLLER')
                if self.DB_SAVE:
                    service.save()
                else:
                    if self.verbosity:self.info('service {} not saved, DB_SAVE = {}'.format(service, self.DB_SAVE))

                service.access_level = None

            self.process_service_commands(service, service_config.get('service_commands', []))
            self.process_page_groups(service, service_config.get('pages', []))

    def info(self, s):
        self.command.stdout.write(self.command.style.SUCCESS(s))

    def set_indent(self, level):
        self.indent_level = level

    def get_indent(self):
        return self.indent_level

    def log(self, trace, n=False):
        indent = ' ' * (self.indent_level * 2)
        if n:
            print '\n{}{}'.format(indent, trace),
        else:
            print '{}{}'.format(indent, trace),


class Command(BaseCommand):
    help = 'Generate IIC models from a set of configs'

    def add_arguments(self, parser):
        parser.add_argument('configs_file', type=str)

    def handle(self, *args, **options):
        configs = options['configs_file']

        configs_file_abs = os.path.abspath(configs)
        print configs_file_abs

        with open(configs_file_abs) as data_file:
            configs_json = json.load(data_file)

        iic = IicGenerator(self, configs_json, start_level=2, db_save=True)
        iic.gen()

        configs_file_abs_out = configs_file_abs+'.out.json'

        with open(configs_file_abs_out,'w') as data_file:
            json.dump(configs_json, data_file)

        self.stdout.write(self.style.SUCCESS('\nSuccess --- check {}'.format(data_file.name)))
