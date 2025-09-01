/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        const orm = useService("orm");

        onMounted(async () => {
            debugger;
            try {
                const model = this.props.threadModel;
                const companyId = session.user_companies['current_company'];
                const userId = user.userId;
                if (companyId && model) {
                    const result = await orm.call("access.management", "get_chatter_hide_details", [
                        userId,
                        companyId,
                        model,
                    ]);

                    if (!result) return;

                    const tryRemove = (selector) => {
                        const timer = setInterval(() => {
                            const elements = document.querySelectorAll(selector);
                            if (elements && elements.length) {
                                elements.forEach((el) => {
                                    el.classList.add("d-none");
                                });
                                clearInterval(timer);
                            }
                        }, 50);
                        setTimeout(() => clearInterval(timer), 3000);
                    };

                    if (!result.hide_send_mail) {
                        tryRemove(".o-mail-Chatter-sendMessage");
                    }
                    if (!result.hide_log_notes) {
                        tryRemove(".o-mail-Chatter-logNote");
                    }
                    if (!result.hide_schedule_activity) {
                        tryRemove(".o-mail-Chatter-activity");
                    }
                    if (!result.hide_chatter) {
                        tryRemove(".o-mail-ChatterContainer");
                    }
                    if (!result["hide_send_mail"] && !result["hide_log_notes"] && !result["hide_schedule_activity"]) {
                        return
                    }
                }
            } catch (error) {
                console.error("Failed to apply chatter visibility rules:", error);
            }
        });
    },
});
