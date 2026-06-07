document.addEventListener("DOMContentLoaded", async ()=> {
    const urlParams = new URLSearchParams(window.location.search)
    const itemId = urlParams.get('id')
    if(!itemId){
        alert("Товар не найдет или не выбран!!!!")
        window.location.href = "/"
        return
    }
    const API_URL = `/items/${itemId}`;
    try{
        const response = await fetch(API_URL);
        if (!response.ok){
            throw new Error("Товар не найден на сервере")
        }
        const item = await response.json();
        document.getElementById('item-name').textContent = item.name
        document.getElementById('item-sector').textContent = item.storage_sector
        document.getElementById('item-quantity').textContent = item.quantity
        document.getElementById('item-weight').textContent = item.weight

        const imageElement = document.getElementById('item-image')
        if(item.image_url){
            imageElement.src = item.image_url
        }
        else{
            imageElement.src = "/static/img/default.jpg"
        }
        if(item.is_dangerous){
            document.getElementById('danger-badge').style.display = 'block';
        }
    
    } catch(error){
        console.error("ошибка:", error)
        document.getElementById('item-name').textContent = "Ошибка загрузки элемента"
    }
})