export default class {
    constructor() {
        this.path = "";
    }

    async getHTML() {
        let result = await fetch(this.path, {
            method: 'GET', 
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            return data;
        })
        .catch(err => //console.log(err));

        ////console.log(result);
        return result;
    }
}

    