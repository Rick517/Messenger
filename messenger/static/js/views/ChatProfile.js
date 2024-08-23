import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(chat_id) {
        super();
        this.path = '/view/chat_profile/' + chat_id;
    }
}