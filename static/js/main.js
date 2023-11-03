document.addEventListener("DOMContentLoaded", function() {
    var likeForms = document.getElementsByClassName('movie-form');

    for (let i = 0; i < likeForms.length; i++) {
        var id = "like-button" + (i + 1); 

        var movie_liked=false;

        var likeButton = likeForms[i].querySelector('#' + id);
        if(!likeButton){
            likeButton=likeForms[i].querySelector('#like-button')
        }

        if (likeButton) {
            likeButton.addEventListener("click", function(e) {
                e.preventDefault();
                var formData = new FormData(likeForms[i]);

                fetch('/like-movie', {
                    method: 'POST',
                    body: formData,
                }).then(res => res.json()).then(data => {
                    console.log(data);
                    alert("You liked a movie")
                })
                fetch('/update-user-profile',{
                    method:"POST",
                    body:formData,
                }).then(res=>res.json()).then(data=>console.log(data));
            });
        }
    }
    
});
