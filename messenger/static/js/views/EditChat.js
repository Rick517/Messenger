import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(chat_id) {
        super();
        this.path = '/view/edit_chat/' + chat_id;
    }
}