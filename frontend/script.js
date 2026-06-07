const savedTheme = localStorage.getItem('theme');
const container = document.getElementById('items-container');
let userId = localStorage.getItem('warehouse_user_id')
if (!userId){
    Math.random()
    userId = 'user' + Math.random().toString(36).slice(2,11)
    localStorage.setItem('warehouse_user_id', userId)
    console.log("Создан новый ид пользователя:", userId)
}
else{
    console.log("Пользователь уже есть:", userId)
}




if (savedTheme === 'dark'){
    document.body.classList.add('dark-theme')
}

function renderCards(items){
    container.innerHTML = "";
    items.forEach(item =>{
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class='card-badge'> Сектор ${item.storage_sector}</div>
            <h3 class="card-title"> ${item.name} </h3>
            <p class="card-description"> Вес объекта: ${item.weight} кг. </p>
            <div class="card-stats">
                <span> Кол-во <b>${item.quantity}</b> </span>
                <span class="card-extra"> ${item.is_dangerous ? 'Опасно!' : 'Безопасно'} </span>
            </div>
            <button class="btn-more" onclick="window.location.href='item.html?id=${item.id}'">Подробнее </button>
            <button class="btn-more" onclick="addToCart(${item.id})"> в корзину </button>
            `;  
        container.appendChild(card)
    });
}

function loadItemsFromServer(){
    const API_URL = '/items'
    fetch(API_URL)
        .then(response =>{
            if(!response.ok){
                throw new Error("Ошибка: сервер не хочет отвечать нам:( ")
            }
            return response.json();
        })
        .then(data=>{
            renderCards(data);
        })
        .catch(error=>{
            container.innerHTML = "<h3>Ошибка подключения к серверу</h3>"
        })
}

const themeBtn = document.querySelector('#theme-toggle');
if (document.body.classList.contains('dark-theme')){
    themeBtn.innerText = 'Светлая тема';
}
themeBtn.addEventListener("click", () =>{
    document.body.classList.toggle('dark-theme');
    if(document.body.classList.contains('dark-theme')){
        localStorage.setItem('theme', 'dark');
        themeBtn.innerText = 'Светлая тема'
    } else{
        localStorage.setItem('theme', 'light');
        themeBtn.innerText = '🌙Темная тема';
    }
});
async function addToCart(itemId) {
    const API_URLL = `/cart/add/${itemId}?user_id=${userId}`
    try{
        const response = await fetch(API_URLL, {
            method: 'POST'
        })
        if(response.ok){
            const data = await response.json()
            alert("Товар добавлен в корзину")
            console.log("Состояние нашей корзины на серевере:", data.cart)
        } else{
            alert("Ошибка: не удалось добавить товар")
        }
    } catch(error){
        console.error("Ошибка:", error)
        alert("Сегодня выходной у разрабов!")
    }
}
loadItemsFromServer();