function toggleMenu() {
    var menu = document.getElementById("optionsMenu");
    menu.classList.toggle("show");
  }

  // Add a new function to handle image click
  function toggleMenuByImage(event) {
    // Prevent the click event from propagating to the parent element (button)
    event.stopPropagation();
    // Trigger the toggleMenu function
    toggleMenu();
  }

  window.onclick = function(event) {
    if (!event.target.matches('.menu-toggle')) {
      var menus = document.getElementsByClassName("options");
      var i;
      for (i = 0; i < menus.length; i++) {
        var openMenu = menus[i];
        if (openMenu.classList.contains('show')) {
          openMenu.classList.remove('show');
        }
      }
    }
  }
