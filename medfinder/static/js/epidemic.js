document.addEventListener("DOMContentLoaded", function() {
  let activeFieldComponent = document.getElementById("id_active");
  let contentCompoents = document.getElementsByClassName("field-content");
  if (contentCompoents.length === 0) return;  
  let contentCompoent = contentCompoents[0];
  activeFieldComponent.addEventListener('click', function() { 
    contentCompoent.style.display = activeFieldComponent.checked ? "block" : "none";      
    })
  }
);