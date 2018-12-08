(() => {

  function handleFormSubmit({ endpoint, method, body = null }) {
    return fetch(`http://localhost:5000/${endpoint}`, {
      method: method,
      body: body,
      redirect: 'manual'
    });
  }
  
  const deleteCategory = document.getElementById("delete-category");
  if (deleteCategory) {
    deleteCategory.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "DELETE", endpoint: `categories/${deleteCategory.dataset.categoryId}/` })
        .then(() => window.location = `http://localhost:5000/categories`)
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const editCategory = document.getElementById("edit-category");
  if (editCategory) {
    editCategory.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "PUT", endpoint: `categories/${editCategory.dataset.categoryId}/`, body: new FormData(editCategory) })
        .then(() => location.reload())
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const deleteItem = document.getElementById("delete-item");
  if (deleteItem) {
    deleteItem.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "DELETE", endpoint: `categories/${deleteItem.dataset.categoryId}/items/${deleteItem.dataset.itemId}/` })
        .then(() => window.location = `http://localhost:5000/categories/${deleteItem.dataset.categoryId}`)
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const editItem = document.getElementById("edit-item");
  if (editItem) {
    editItem.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "PUT", endpoint: `categories/${editItem.dataset.categoryId}/items/${editItem.dataset.itemId}/`, body: new FormData(editItem) })
        .then(() => location.reload())
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

})();