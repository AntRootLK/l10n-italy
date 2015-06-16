# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 Andrea Cometa.
#    Email: info@andreacometa.it
#    Web site: http://www.andreacometa.it
#    Copyright (C) 2012 Agile Business Group sagl (<http://www.agilebg.com>)
#    Copyright (C) 2012 Domsense srl (<http://www.domsense.com>)
#    Copyright (C) 2012 Associazione OpenERP Italia
#    (<http://www.openerp-italia.org>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models, exceptions, api, _


# -------------------------------------------------------
#        RIBA ISSUE
# -------------------------------------------------------
class riba_issue(models.TransientModel):
    _name = "riba.issue"
    _description = "Ricevute bancarie issue"
    configuration_id = fields.Many2one(
        'riba.configuration', string='Configuration', required=True)

    @api.one
    def create_list(self):
        def create_rdl(countme, bank_id, rd_id, date_maturity, partner_id,
                       acceptance_account_id):
            rdl = {
                'sequence': countme,
                'bank_id': bank_id,
                'list_id': rd_id,
                'due_date': date_maturity,
                'partner_id': partner_id,
                'state': 'draft',
                'acceptance_account_id': acceptance_account_id,
            }
            return riba_list_line.create(rdl)

        '''
            Qui creiamo la distinta
        '''
        # wizard_obj = self.browse(cr, uid, ids)[0]
        # active_ids = context and context.get('active_ids', [])
        riba_list = self.env['riba.list']
        riba_list_line = self.env['riba.list.line']
        riba_list_move_line = self.env['riba.list.move.line']
        move_line_obj = self.env['account.move.line']

        # create distinta
        rd = {
            'name': self.env['ir.sequence'].get('seq.riba.list'),
            'config_id': self.configuration_id.id,
            'user_id': self._uid,
            'date_created': fields.Date.context_today(self),
        }
        rd_id = riba_list.create(rd).id

        # group by partner and due date
        grouped_lines = {}
        move_lines = move_line_obj.search(
            [('id', 'in', self._context['active_ids'])])
        # move_lines = move_line_obj.browse(move_line_ids)
        # import pdb; pdb.set_trace()
        for move_line in move_lines:
            if move_line.partner_id.group_riba:
                if not grouped_lines.get((move_line.partner_id.id,
                                          move_line.date_maturity), False):
                    grouped_lines[(move_line.partner_id.id,
                                   move_line.date_maturity)] = []
                grouped_lines[(move_line.partner_id.id,
                               move_line.date_maturity)].append(move_line)

        # create lines
        countme = 1

        for move_line in move_lines:
            if move_line.partner_id.bank_ids:
                bank_id = move_line.partner_id.bank_ids[0]
            else:
                raise exceptions.Warning(
                    _('Attention!'),
                    _('Partner %s has not bank!!!') %
                    move_line.partner_id.name)
            if move_line.partner_id.group_riba:
                for key in grouped_lines:
                    if (key[0] == move_line.partner_id.id and
                            key[1] == move_line.date_maturity):
                        rdl_id = create_rdl(
                            countme, bank_id.id, rd_id,
                            move_line.date_maturity, move_line.partner_id.id,
                            self.configuration_id.acceptance_account_id.id)
                        # total = 0.0
                        # invoice_date_group = ''
                        for grouped_line in grouped_lines[key]:
                            riba_list_move_line.create({
                                'riba_line_id': rdl_id,
                                'amount': grouped_line.amount_residual,
                                'move_line_id': grouped_line.id,
                                })
                        del grouped_lines[key]
                        break
            else:
                rdl_id = create_rdl(
                    countme, bank_id.id, rd_id, move_line.date_maturity,
                    move_line.partner_id.id,
                    self.configuration_id.acceptance_account_id.id).id
                riba_list_move_line.create({
                    'riba_line_id': rdl_id,
                    'amount': move_line.amount_residual,
                    'move_line_id': move_line.id,
                    })

            countme += 1

        # ----- show list form
        mod_obj = self.env['ir.model.data']
        res = mod_obj.get_object_reference(
            'l10n_it_ricevute_bancarie', 'view_riba_list_form')
        res_id = res and res[1] or False,
        return {
            'name': 'Distinta',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': res_id,
            'res_model': 'riba.list',
            'type': 'ir.actions.act_window',
            # 'nodestroy': True,
            'target': 'current',
            'res_id': rd_id or False,
        }

riba_issue()
