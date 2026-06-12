async function addItem() {
    const name = document.getElementById("name").value;
    const category = document.getElementById("category").value;
    const quantity = document.getElementById("quantity").value;
    const expiry = document.getElementById("expiry").value;

    await fetch('/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, category, quantity, expiry})
    });

    loadItems();
}

async function loadItems() {
    const response = await fetch('/items');
    const items = await response.json();

    const table = document.getElementById("inventory");
    table.innerHTML = "";

    items.forEach(item => {
        const row = `<tr>
            <td>${item.name}</td>
            <td>${item.category}</td>
            <td>${item.quantity}</td>
            <td>${item.expiry}</td>
            <td>${item.days_left}</td>
            <td><button onclick="deleteItem('${item.name}')">Delete</button></td>
        </tr>`;
        table.innerHTML += row;
    });
}

async function deleteItem(name) {
    await fetch(`/delete/${name}`, {method: 'DELETE'});
    loadItems();
}

window.onload = loadItems;