(function() {

  // Because HTML forms cannot make PUT or DELETE requests,
  // we use this function to make the request, and follow through server redirects.
  function handleFormSubmit({ endpoint, method, body = null }) {
    return fetch(`/${endpoint}`, {
      method: method,
      body: body,
      redirect: 'follow'
    })
      .then(res => window.location = res.url);
  }
  
  const deleteCategory = document.getElementById("delete-category");
  if (deleteCategory) {
    deleteCategory.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "DELETE", endpoint: `categories/${deleteCategory.dataset.categoryId}/delete` })
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const editCategory = document.getElementById("edit-category");
  if (editCategory) {
    editCategory.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "PUT", endpoint: `categories/${editCategory.dataset.categoryId}/edit`, body: new FormData(editCategory) })
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const deleteItem = document.getElementById("delete-item");
  if (deleteItem) {
    deleteItem.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "DELETE", endpoint: `categories/${deleteItem.dataset.categoryId}/items/${deleteItem.dataset.itemId}/delete` })
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

  const editItem = document.getElementById("edit-item");
  if (editItem) {
    editItem.addEventListener("submit", (evt) => {
      evt.preventDefault();
      handleFormSubmit({ method: "PUT", endpoint: `categories/${editItem.dataset.categoryId}/items/${editItem.dataset.itemId}/edit`, body: new FormData(editItem) })
        .catch((err) => {
          console.log("Error: ", err);
        });
    });
  }

})();