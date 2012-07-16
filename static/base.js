var errormessage = "An error occurred!  Please check your internet connection and try again.  If the problem persists, please <a href='/contact.html'>contact us</a>.";

// display a message
function flash(message)
{
    $("#flash").html(message).fadeIn(400);
}

// hide message
function hideflash()
{
    $("#flash").fadeOut(300);
}

// ajax spinner
function spin()
{
    $("div#spinner").fadeIn("fast");
}

function hidespinner()
{
    $("div#spinner").fadeOut("fast");
}

// show error message
function flasherror()
{
    flash("An error occurred!  Please check your internet connection and try again.  If the problem persists, please <a href='/contact.html'>contact us</a>.");
}

// zebra stripe result tables
function stripetables() {
    $("table.stripe tr").removeClass("alt");
    $("table.stripe tr:even").not(".abstracts").addClass("alt");

    $("table.stripe tr")
    .mouseover(function() {
        $(this).addClass("over");
    })
    .mouseout(function() {
        $(this).removeClass("over");
    });
}

$(document).ready(function() {
    stripetables();
    
    // fade the flash box when we move the mouse over it, hide it when it's clicked
    $("#flash")
    .click(function() {
        $(this).hide();
    })
    .mouseover(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 0.3);
    })
    .mouseout(function() {
        if ($(this).is(":visible")) $(this).fadeTo(200, 1);
    });
    
    
});
