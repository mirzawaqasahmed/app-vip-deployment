# -*- mode: python; python-indent: 4 -*-
import ncs
from ncs.application import Service
from ncs.dp import Action


def verify_cr_approval(cr_number):
    # this is where we can validate that a CR for this VIP]
    # deployment is approved.
    return True


# ---------------
# ACTIONS EXAMPLE
# ---------------
class DoubleAction(Action):
    @Action.action
    def cb_action(self, uinfo, name, kp, input, output):
        self.log.info('action name: ', name)
        self.log.info('action input.number: ', input.number)

        # Updating the output data structure will result in a response
        # being returned to the caller.
        output.result = input.number * 2


# ------------------------
# SERVICE CALLBACK EXAMPLE
# ------------------------
class ServiceCallbacks(Service):

    # The create() callback is invoked inside NCS FASTMAP and
    # must always exist.
    @Service.create
    def cb_create(self, tctx, root, service, proplist):
        if verify_cr_approval(service.change_request):
            self.log.info('Service create(service=', service._path, ')')
            self.log.info(dir(service))
            for ltm in service.ltm:
                vip_vars = ncs.template.Variables()
                vip_vars.add('DEVICE', ltm.device)
                vip_vars.add('VIP_NAME', service.name)
                vip_vars.add('POOL_NAME', 'pool_' + service.name)
                vip_vars.add('VIP_DESTINATION', ltm.vip_address + ':http')
                vip_vars.add('PROTOCOL', 'tcp')
                vip_vars.add('SOURCE', '0.0.0.0/0')
                vip_vars.add('PROFILE', 'tcp')
                vip_vars.add('VIP_MASK', '255.255.255.255')
                vip_vars.add('DATACENTER', 'UTC-A')

                self.log.info("Rendering Node/Pool Template")
                self.log.info("avail vars in rendering: {}".format(vip_vars))
                pool_template = ncs.template.Template(service)
                pool_template.apply('ltm-node-pool-template', vip_vars)

                self.log.info("Rendering VIP Template ")
                self.log.info("avail vars in rendering: {}".format(vip_vars))
                template = ncs.template.Template(service)
                template.apply('ltm-vip-template', vip_vars)

                # each LTM VIP needs to be configured on each GTM
                for gtm in service.gtm:
                    vip_vars.add('GTM_DEVICE', gtm.device)
                    # TODO need to expose somehow
                    vip_vars.add('MONITOR_NAME', 'monitor_tcp_80_30i_120t')
                    member_name = service.name + ":" + service.name
                    vip_vars.add('MEMBER_NAME', member_name)
                    vip_vars.add('GTM_SERVER_ADDRESS', ltm.vip_address)

                    self.log.info("Rendering GTM Template with vars")
                    self.log.info(vip_vars)
                    template.apply('gtm-template', vip_vars)

    # The pre_modification() and post_modification() callbacks are optional,
    # and are invoked outside FASTMAP. pre_modification() is invoked before
    # create, update, or delete of the service, as indicated by the enum
    # ncs_service_operation op parameter. Conversely
    # post_modification() is invoked after create, update, or delete
    # of the service. These functions can be useful e.g. for
    # allocations that should be stored and existing also when the
    # service instance is removed.

    # @Service.pre_lock_create
    # def cb_pre_lock_create(self, tctx, root, service, proplist):
    #     self.log.info('Service plcreate(service=', service._path, ')')

    # @Service.pre_modification
    # def cb_pre_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')

    # @Service.post_modification
    # def cb_post_modification(self, tctx, op, kp, root, proplist):
    #     self.log.info('Service premod(service=', kp, ')')


# ---------------------------------------------
# COMPONENT THREAD THAT WILL BE STARTED BY NCS.
# ---------------------------------------------
class Main(ncs.application.Application):
    def setup(self):
        # The application class sets up logging for us. It is accessible
        # through 'self.log' and is a ncs.log.Log instance.
        self.log.info('Main RUNNING')

        # Service callbacks require a registration for a 'service point',
        # as specified in the corresponding data model.
        #
        self.register_service('app-vip-deployment-servicepoint',
                              ServiceCallbacks)

        # When using actions, this is how we register them:
        #
        self.register_action('app-vip-deployment-action', DoubleAction)

        # If we registered any callback(s) above, the Application class
        # took care of creating a daemon (related to the service/action point).

        # When this setup method is finished, all registrations are
        # considered done and the application is 'started'.

    def teardown(self):
        # When the application is finished (which would happen if NCS went
        # down, packages were reloaded or some error occurred) this teardown
        # method will be called.

        self.log.info('Main FINISHED')
