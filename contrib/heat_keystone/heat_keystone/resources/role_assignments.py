#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from heat.common import exception
from heat.common.i18n import _
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.engine import support


class KeystoneRoleAssignment(resource.Resource):
    '''
    Keystone Role assignment class implements role assignments between
    user/groups and project/domain.

    heat_template_version: 2013-05-23

    parameters:
      ... Group or User parameters
      group_role:
        type: string
        description: role
      group_role_domain:
        type: string
        description: group role domain
      group_role_project:
        type: string
        description: group role project

    resources:
      admin_group:
        type: OS::Keystone::Group OR OS::Keystone::User
        properties:
          ... Group or User properties
          roles:
            - role: {get_param: group_role}
              domain: {get_param: group_role_domain}
            - role: {get_param: group_role}
              project: {get_param: group_role_project}
    '''

    support_status = support.SupportStatus(
        version='2015.1',
        message=_('Supported versions: keystone v3'))

    PROPERTIES = (
        ROLES
    ) = (
        'roles'
    )

    _ROLES_MAPPING_PROPERTIES = (
        ROLE, DOMAIN, PROJECT
    ) = (
        'role', 'domain', 'project'
    )

    properties_schema = {
        ROLES: properties.Schema(
            properties.Schema.LIST,
            _('List of role assignments.'),
            schema=properties.Schema(
                properties.Schema.MAP,
                _('Map between role with either project or domain.'),
                schema={
                    ROLE: properties.Schema(
                        properties.Schema.STRING,
                        _('Keystone role'),
                        required=True,
                        constraints=([constraints.
                                     CustomConstraint('keystone.role')])
                    ),
                    PROJECT: properties.Schema(
                        properties.Schema.STRING,
                        _('Keystone project'),
                        constraints=([constraints.
                                     CustomConstraint('keystone.project')])
                    ),
                    DOMAIN: properties.Schema(
                        properties.Schema.STRING,
                        _('Keystone domain'),
                        constraints=([constraints.
                                     CustomConstraint('keystone.domain')])
                    ),
                }
            ),
            update_allowed=True
        )
    }

    def _add_role_assignments_to_group(self, group_id, role_assignments):
        for role_assignment in self._normalize_to_id(role_assignments):
            if role_assignment.get(self.PROJECT) is not None:
                self.keystone().client.roles.grant(
                    role=role_assignment.get(self.ROLE),
                    project=role_assignment.get(self.PROJECT),
                    group=group_id
                )
            elif role_assignment.get(self.DOMAIN) is not None:
                self.keystone().client.roles.grant(
                    role=role_assignment.get(self.ROLE),
                    domain=role_assignment.get(self.DOMAIN),
                    group=group_id
                )

    def _add_role_assignments_to_user(self, user_id, role_assignments):
        for role_assignment in self._normalize_to_id(role_assignments):
            if role_assignment.get(self.PROJECT) is not None:
                self.keystone().client.roles.grant(
                    role=role_assignment.get(self.ROLE),
                    project=role_assignment.get(self.PROJECT),
                    user=user_id
                )
            elif role_assignment.get(self.DOMAIN) is not None:
                self.keystone().client.roles.grant(
                    role=role_assignment.get(self.ROLE),
                    domain=role_assignment.get(self.DOMAIN),
                    user=user_id
                )

    def _remove_role_assignments_from_group(self, group_id, role_assignments):
        for role_assignment in self._normalize_to_id(role_assignments):
            if role_assignment.get(self.PROJECT) is not None:
                self.keystone().client.roles.revoke(
                    role=role_assignment.get(self.ROLE),
                    project=role_assignment.get(self.PROJECT),
                    group=group_id
                )
            elif role_assignment.get(self.DOMAIN) is not None:
                self.keystone().client.roles.revoke(
                    role=role_assignment.get(self.ROLE),
                    domain=role_assignment.get(self.DOMAIN),
                    group=group_id
                )

    def _remove_role_assignments_from_user(self, user_id, role_assignments):
        for role_assignment in self._normalize_to_id(role_assignments):
            if role_assignment.get(self.PROJECT) is not None:
                self.keystone().client.roles.revoke(
                    role=role_assignment.get(self.ROLE),
                    project=role_assignment.get(self.PROJECT),
                    user=user_id
                )
            elif role_assignment.get(self.DOMAIN) is not None:
                self.keystone().client.roles.revoke(
                    role=role_assignment.get(self.ROLE),
                    domain=role_assignment.get(self.DOMAIN),
                    user=user_id
                )

    def _normalize_to_id(self, role_assignment_prps):
        role_assignments = []
        if role_assignment_prps is None:
            return role_assignments

        for role_assignment in role_assignment_prps:
            role = role_assignment.get(self.ROLE)
            project = role_assignment.get(self.PROJECT)
            domain = role_assignment.get(self.DOMAIN)

            role_assignments.append({
                self.ROLE: (self.client_plugin('keystone').
                            get_role_id(role)),
                self.PROJECT: (self.client_plugin('keystone').
                               get_project_id(project)) if project else None,
                self.DOMAIN: (self.client_plugin('keystone').
                              get_domain_id(domain)) if domain else None
            })
        return role_assignments

    @staticmethod
    def _find_diff(updated_prps, stored_prps):
        updated_role_project_assignments = []
        updated_role_domain_assignments = []

        # Split the properties into two set of role assignments
        # (project, domain) from updated properties
        for role_assignment in updated_prps or []:
            if role_assignment.get(KeystoneRoleAssignment.PROJECT) is not None:
                updated_role_project_assignments.append(
                    '%s:%s' % (
                        role_assignment[KeystoneRoleAssignment.ROLE],
                        role_assignment[KeystoneRoleAssignment.PROJECT]))
            elif (role_assignment.get(KeystoneRoleAssignment.DOMAIN)
                  is not None):
                updated_role_domain_assignments.append(
                    '%s:%s' % (role_assignment[KeystoneRoleAssignment.ROLE],
                               role_assignment[KeystoneRoleAssignment.DOMAIN]))

        stored_role_project_assignments = []
        stored_role_domain_assignments = []

        # Split the properties into two set of role assignments
        # (project, domain) from updated properties
        for role_assignment in (stored_prps or []):
            if role_assignment.get(KeystoneRoleAssignment.PROJECT) is not None:
                stored_role_project_assignments.append(
                    '%s:%s' % (
                        role_assignment[KeystoneRoleAssignment.ROLE],
                        role_assignment[KeystoneRoleAssignment.PROJECT]))
            elif (role_assignment.get(KeystoneRoleAssignment.DOMAIN)
                  is not None):
                stored_role_domain_assignments.append(
                    '%s:%s' % (role_assignment[KeystoneRoleAssignment.ROLE],
                               role_assignment[KeystoneRoleAssignment.DOMAIN]))

        new_role_assignments = []
        removed_role_assignments = []
        # NOTE: finding the diff of list of strings is easier by using 'set'
        #       so properties are converted to string in above sections
        # New items
        for item in (set(updated_role_project_assignments) -
                     set(stored_role_project_assignments)):
            new_role_assignments.append(
                {KeystoneRoleAssignment.ROLE: item[:item.find(':')],
                 KeystoneRoleAssignment.PROJECT: item[item.find(':') + 1:]}
            )

        for item in (set(updated_role_domain_assignments) -
                     set(stored_role_domain_assignments)):
            new_role_assignments.append(
                {KeystoneRoleAssignment.ROLE: item[:item.find(':')],
                 KeystoneRoleAssignment.DOMAIN: item[item.find(':') + 1:]}
            )

        # Old items
        for item in (set(stored_role_project_assignments) -
                     set(updated_role_project_assignments)):
            removed_role_assignments.append(
                {KeystoneRoleAssignment.ROLE: item[:item.find(':')],
                 KeystoneRoleAssignment.PROJECT: item[item.find(':') + 1:]}
            )
        for item in (set(stored_role_domain_assignments) -
                     set(updated_role_domain_assignments)):
            removed_role_assignments.append(
                {KeystoneRoleAssignment.ROLE: item[:item.find(':')],
                 KeystoneRoleAssignment.DOMAIN: item[item.find(':') + 1:]}
            )

        return new_role_assignments, removed_role_assignments

    def handle_create(self, user_id=None, group_id=None):
        if self.properties.get(self.ROLES) is not None:
            if user_id is not None:
                self._add_role_assignments_to_user(
                    user_id,
                    self.properties.get(self.ROLES))
            elif group_id is not None:
                self._add_role_assignments_to_group(
                    group_id,
                    self.properties.get(self.ROLES))

    def handle_update(self, user_id=None, group_id=None, prop_diff=None):
        (new_role_assignments,
         removed_role_assignments) = KeystoneRoleAssignment._find_diff(
            prop_diff.get(self.ROLES),
            self._stored_properties_data.get(self.ROLES))

        if len(new_role_assignments) > 0:
            if user_id is not None:
                self._add_role_assignments_to_user(
                    user_id,
                    new_role_assignments)
            elif group_id is not None:
                self._add_role_assignments_to_group(
                    group_id,
                    new_role_assignments)

        if len(removed_role_assignments) > 0:
            if user_id is not None:
                self._remove_role_assignments_from_user(
                    user_id,
                    removed_role_assignments)
            elif group_id is not None:
                self._remove_role_assignments_from_group(
                    group_id,
                    removed_role_assignments)

    def handle_delete(self, user_id=None, group_id=None):
        if self._stored_properties_data.get(self.ROLES) is not None:
            if user_id is not None:
                self._remove_role_assignments_from_user(
                    user_id,
                    (self._stored_properties_data.
                     get(self.ROLES)))
            elif group_id is not None:
                self._remove_role_assignments_from_group(
                    group_id,
                    (self._stored_properties_data.
                     get(self.ROLES)))

    def validate(self):
        super(KeystoneRoleAssignment, self).validate()

        if self.properties.get(self.ROLES) is not None:
            for role_assignment in self.properties.get(self.ROLES):
                project = role_assignment.get(self.PROJECT)
                domain = role_assignment.get(self.DOMAIN)

                if project is not None and domain is not None:
                    raise exception.ResourcePropertyConflict(self.PROJECT,
                                                             self.DOMAIN)

                if project is None and domain is None:
                    msg = _('Either project or domain must be specified for'
                            ' role %s') % role_assignment.get(self.ROLE)
                    raise exception.StackValidationFailed(message=msg)
