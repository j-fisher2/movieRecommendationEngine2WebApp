document.addEventListener("DOMContentLoaded", function() {
    var likeForms = document.getElementsByClassName('movie-form');

    var genreForms=document.getElementsByClassName('bubble')

    for(let i=0;i<genreForms.length;i++){
        var genre_button=genreForms[i].querySelector('#g'+(i+1))

        if(genre_button){
            genre_button.addEventListener("click",(e)=>{
                e.preventDefault();
                
                var formData=new FormData(genreForms[i]);
                fetch('/find-genres',{
                    method:"POST",
                    body:formData,
                }).then(res=>res.json()).then(data=>{
                    var idx=0
                    var parent = document.getElementById("poster-container");
                    var children = parent.getElementsByClassName("poster");
                    for(let movie in data){
                        if (data.hasOwnProperty(movie)) {
                            if(children&&children[idx]){
                                children[idx].src=data[movie]
                                idx++
                            }
                            else{
                                var child = document.createElement("img");
                                child.src = data[movie]; 
                                child.className="poster"
                                parent.appendChild(child);
                            }
                        }
                    }
                })
            })
        }
    }

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
