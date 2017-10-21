# example
heri_login_register = [  # list of services
    dict(
        name="CREATE CLIENT",
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

mduka_agent_create_client = [  # list of services
    dict(
        name="CREATE RETAILER",
        service_commands=[
            dict(
                name='get_section',
            ),

            dict(
                name='create_client',
            )
        ],
        page_groups=[
            dict(
                name='Home',
                item_level=-1,  # next item_level
                # description='',
                icon=None,
                gateways=['M-Duka'],
                pages=[

                    dict(
                        name='Retailers',
                        description='Retailers',
                        icon=None,
                        item_level=-1,
                        access_levels=['AGENT'],
                        services=['HOME'],
                        gateways=['M-Duka'],
                        page_input_groups=[
                            dict(
                                name='Create Retailer',
                                description='Create Retailer',
                                icon=None,
                                item_level=-1,
                                input_variable=True,  # True is FORM, False is HIDDEN FORM
                                service = 'CREATE RETAILER',
                                section_size='24|24|24',
                                section_height=900,
                                gateways=[],
                                page_inputs=[
                                    dict(
                                        name='msisdn',
                                        variable_type='MSISDN INPUT',
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
                                        name='full_name',
                                        variable_type='TEXT INPUT',
                                        validate_min=2,
                                        validate_max=60

                                    ),
                                    dict(
                                        name='password',
                                        variable_type='TEXT INPUT',
                                        validate_min=0,
                                        validate_max=30

                                    ),
                                    dict(
                                        name='Create Retailer',
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
