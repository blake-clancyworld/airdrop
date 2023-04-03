# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class MassAirdropList(models.Model):
    """Model of a contact list. """
    _name = 'airdrop.list'
    _order = 'name'
    _description = 'Airdrop List'
    _airdrop_enabled = True
    # As this model has his own data merge, avoid to enable the generic data_merge on that model.
    _disable_data_merge = True

    name = fields.Char(string='Airdrop List', required=True)
    active = fields.Boolean(default=True)
    contact_count = fields.Integer(compute="_compute_airdrop_list_statistics", string='Number of Contacts')
    contact_ids = fields.Many2many(
        'res.partner', 'airdrop_contact_list_rel', 'list_id', 'contact_id',
        string='Contacts', copy=False)
    airdrop_count = fields.Integer(compute="_compute_airdrop_list_count", string="Number of Airdrop")
    airdrop_ids = fields.Many2many('airdrop.airdrop', 'mail_mass_airdrop_list_rel', string='Mass Airdrops', copy=False)
    product_id = fields.Many2one('product.product', string='Product', required=True,
                                 domain=[('type', '=', 'product')], ondelete='cascade')

    contact_ids = fields.Many2many(
        'airdrop.contact', 'airdrop_contact_list_rel', 'list_id', 'contact_id',
        string='Airdrop Lists', copy=False)
    airdrop_ids = fields.Many2many('airdrop.airdrop', 'mail_mass_airdrop_list_rel', string='Mass Airdrops', copy=False)
    subscription_ids = fields.One2many(
        'airdrop.contact.subscription', 'list_id', string='Subscription Information',
        copy=True, depends=['contact_ids'])


    # ------------------------------------------------------
    # COMPUTE / ONCHANGE
    # ------------------------------------------------------

    def _compute_airdrop_list_count(self):
        for airdrop_list in self:
            airdrop_list.airdrop_count = len(airdrop_list.airdrop_ids)


    def _compute_airdrop_list_statistics(self):
        contact_statistics_per_airdrop = self._fetch_contact_statistics()

    # 2. Fetch bounce data
    # Optimized SQL way of fetching the count of contacts that have
    # at least 1 message bouncing for passed airdrop.lists """
        bounce_per_airdrop = {}
        if self.ids:
            sql = '''
                SELECT mclr.list_id, COUNT(DISTINCT mc.id)
                FROM airdrop_contact mc
                LEFT OUTER JOIN airdrop_contact_list_rel mclr
                ON mc.id = mclr.contact_id
                WHERE mc.message_bounce > 0
                AND mclr.list_id in %s
                GROUP BY mclr.list_id
            '''
            self.env.cr.execute(sql, (tuple(self.ids),))
            bounce_per_airdrop = dict(self.env.cr.fetchall())

    # 3. Compute and assign all counts / pct fields
        for airdrop_list in self:
            contact_counts = contact_statistics_per_airdrop.get(airdrop_list.id, {})
            for field, value in contact_counts.items():
                if field in self._fields:
                    airdrop_list[field] = value

            if airdrop_list.contact_count != 0:
                airdrop_list.contact_pct_bounce = 100 * (bounce_per_airdrop.get(airdrop_list.id, 0) / airdrop_list.contact_count)
            else:
                airdrop_list.contact_pct_bounce = 0


    # ------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------

    def write(self, vals):
        # Prevent archiving used airdrop list
        if 'active' in vals and not vals.get('active'):
            mass_airdrops = self.env['airdrop.airdrop'].search_count([
                ('state', '!=', 'done'),
                ('contact_list_ids', 'in', self.ids),
            ])

            if mass_airdrops > 0:
                raise UserError(_("At least one of the airdrop list you are trying to archive is used in an ongoing airdrop campaign."))

        return super(MassAirdropList, self).write(vals)

    def name_get(self):
        return [(list.id, "%s (%s)" % (list.name, list.contact_count)) for list in self]

    def copy(self, default=None):
        self.ensure_one()

        default = dict(default or {},
                       name=_('%s (copy)', self.name),)
        return super(AirdropList, self).copy(default)


    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_view_contacts(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mass_airdrop.action_view_mass_airdrop_contacts")
        action['domain'] = [('list_ids', 'in', self.ids)]
        action['context'] = {'default_list_ids': self.ids}
        return action

    def action_view_contacts_email(self):
        action = self.action_view_contacts()
        action['context'] = dict(action.get('context', {}), search_default_filter_valid_email_recipient=1)
        return action

    def action_view_airdrops(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_airdrop.airdrop_airdrop_action_mail')
        action['domain'] = [('contact_list_ids', 'in', self.ids)]
        action['context'] = {'default_airdrop_type': 'mail', 'default_airdrop_list_ids': self.ids}
        return action

    def action_view_contacts_bouncing(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_airdrop.action_view_mass_airdrop_contacts')
        action['domain'] = [('list_ids', 'in', self.id)]
        action['context'] = {'default_list_ids': self.ids, 'create': False, 'search_default_filter_bounce': 1}
        return action

    def action_merge(self, src_lists, archive):
        self.ensure_one()
        src_lists |= self
        self.env['airdrop.contact'].flush(['email', 'email_normalized'])
        self.env['airdrop.contact.subscription'].flush(['contact_id', 'opt_out', 'list_id'])
        self.env.cr.execute("""
            INSERT INTO airdrop_contact_list_rel (contact_id, list_id)
            SELECT st.contact_id AS contact_id, %s AS list_id
            FROM (
                SELECT
                    contact.id AS contact_id,
                    contact.email_normalized,
                    list.id AS list_id,
                    row_number() OVER (PARTITION BY email_normalized ORDER BY email_normalized) AS rn
                FROM
                    res_partner contact,
                    airdrop_list list
                WHERE
                    list.id IN %s
                    AND contact.email_normalized NOT IN (
                        SELECT email FROM mail_blacklist WHERE active = TRUE
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM airdrop_contact_list_rel WHERE contact_id = contact.id AND list_id = %s
                    )
            ) st
            WHERE st.rn = 1;
        """, (self.id, tuple(src_lists.ids), self.id))
        self.flush()
        self.invalidate_cache()
        if archive:
            (src_lists - self).action_archive()



    # ------------------------------------------------------
    # UTILITY
    # ------------------------------------------------------

    def _fetch_contact_statistics(self):
        """ Compute number of contacts matching various conditions.
        (see '_get_contact_count_select_fields' for details)

        Will return a dict under the form:
        {
            42: { # 42 being the airdrop list ID
                'contact_count': 52,
                'contact_count_email': 35,
                'contact_count_opt_out': 5,
                'contact_count_blacklisted': 2
            },
            ...
        } """

        res = []
        if self.ids:
            self.env.cr.execute(f'''
                SELECT
                    {','.join(self._get_contact_statistics_fields().values())}
                FROM
                    airdrop_contact_list_rel r
                    {self._get_contact_statistics_joins()}
                WHERE list_id IN %s
                GROUP BY
                    list_id;
            ''', (tuple(self.ids), ))
            res = self.env.cr.dictfetchall()

        contact_counts = {}
        for res_item in res:
            airdrop_list_id = res_item.pop('airdrop_list_id')
            contact_counts[airdrop_list_id] = res_item

        for mass_airdrop in self:
            # adds default 0 values for ids that don't have statistics
            if mass_airdrop.id not in contact_counts:
                contact_counts[mass_airdrop.id] = {
                    field: 0
                    for field in self._get_contact_statistics_fields().keys()
                }

        return contact_counts


    def _get_contact_statistics_fields(self):
        """ Returns fields and SQL query select path in a dictionnary.
        This is done to be easily overridable in subsequent modules.

        - airdrop_list_id             id of the associated airdrop.list
        - contact_count:              all contacts
        - contact_count_email:        all valid emails
        - contact_count_opt_out:      all opted-out contacts
        - contact_count_blacklisted:  all blacklisted contacts """

        return {
            'airdrop_list_id': 'list_id AS airdrop_list_id',
            'contact_count': 'COUNT(*) AS contact_count',
            'contact_count_email': '''
                SUM(CASE WHEN
                        (c.email_normalized IS NOT NULL
                        AND COALESCE(r.opt_out,FALSE) = FALSE
                        AND bl.id IS NULL)
                        THEN 1 ELSE 0 END) AS contact_count_email''',
            'contact_count_opt_out': '''
                SUM(CASE WHEN COALESCE(r.opt_out,FALSE) = TRUE
                    THEN 1 ELSE 0 END) AS contact_count_opt_out''',
            'contact_count_blacklisted': f'''
                SUM(CASE WHEN bl.id IS NOT NULL
                THEN 1 ELSE 0 END) AS contact_count_blacklisted'''
        }

    def _get_contact_statistics_joins(self):
        """ Extracted to be easily overridable by sub-modules (such as mass_airdrop_sms). """
        return """
            LEFT JOIN airdrop_contact c ON (r.contact_id=c.id)
            LEFT JOIN mail_blacklist bl on c.email_normalized = bl.email and bl.active"""
